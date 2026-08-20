# backend/app/api/v1/analytics.py
"""
Analytics endpoints.

Phase 4 wires POST /analytics/descriptive. Every run is persisted as an
AnalysisJob (immutable result history: re-running never mutates a past row).
Descriptive stats are fast enough to run synchronously inline; heavier jobs
(forecasting, segmentation) will be dispatched to Celery in later phases,
reusing this same job/result contract.
"""
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.analysis_job import AnalysisJob, JobStatus, JobType
from app.models.analysis_model import AnalysisModel
from app.models.dataset import Dataset
from app.models.decision import Decision, DecisionPriority
from app.models.decision import DecisionStatus as DecisionStatusModel
from app.models.forecast import Forecast
from app.models.kpi import KPI, KPIType
from app.models.segment import Segment
from app.schemas.analytics import (
    ANOVARequest,
    ANOVAResult,
    DecisionGenerateRequest,
    DecisionGenerateResult,
    DescriptiveRequest,
    DescriptiveResult,
    ForecastRequest,
    ForecastResult,
    KPIRequest,
    KPISuiteResult,
    RegressionRequest,
    RegressionResult,
    SegmentationRequest,
    SegmentationResult,
    ValidationRequest,
    ValidationResult,
)
from app.schemas.errors import ApiError
from app.services.analytics.anova import ANOVAError, compute_anova
from app.services.analytics.descriptive import compute_descriptive_stats
from app.services.analytics.forecasting import ForecastError, compute_forecast
from app.services.analytics.kpis import compute_kpi_suite
from app.services.analytics.regression import RegressionError, compute_regression
from app.services.analytics.segmentation import SegmentationError, compute_segmentation
from app.services.analytics.validation import ValidationError, run_validation_suite
from app.services.datasets.profiling import read_dataset_file
from app.services.decision.engine import DecisionContext, generate_decisions

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _get_owned_dataset(db: AsyncSession, dataset_id: UUID, company_id: UUID) -> Dataset:
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.company_id == company_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "dataset_not_found", "Jeu de données introuvable.")
    return dataset


@router.post("/descriptive", response_model=DescriptiveResult, status_code=status.HTTP_201_CREATED)
async def run_descriptive_analysis(
    payload: DescriptiveRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DescriptiveResult:
    """Compute descriptive statistics + correlation matrix for a dataset."""
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.DESCRIPTIVE,
        config={"columns": payload.columns},
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    try:
        df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        if payload.columns:
            missing_cols = set(payload.columns) - set(df.columns)
            if missing_cols:
                raise ApiError(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "unknown_columns",
                    f"Colonnes inconnues : {', '.join(sorted(missing_cols))}",
                )
        result = compute_descriptive_stats(df, payload.columns or None)
    except ApiError:
        job.status = JobStatus.FAILED
        job.error = "invalid_columns"
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise
    except Exception as exc:  # pragma: no cover - defensive
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "analysis_failed", f"L'analyse a échoué : {exc}"
        ) from exc

    result_payload = DescriptiveResult(
        dataset_id=dataset.id,
        row_count=result.row_count,
        numeric_columns=[
            {
                "column": s.column, "count": s.count, "missing": s.missing, "mean": s.mean,
                "median": s.median, "mode": s.mode, "variance": s.variance, "std": s.std,
                "skewness": s.skewness, "kurtosis": s.kurtosis, "q1": s.q1, "q3": s.q3,
                "iqr": s.iqr, "min": s.min, "max": s.max, "interpretation": s.interpretation,
            }
            for s in result.numeric_columns
        ],
        categorical_columns=[
            {
                "column": s.column, "count": s.count, "missing": s.missing, "unique": s.unique,
                "frequency_table": s.frequency_table, "interpretation": s.interpretation,
            }
            for s in result.categorical_columns
        ],
        correlation=(
            {
                "columns": result.correlation.columns,
                "pearson": result.correlation.pearson,
                "spearman": result.correlation.spearman,
            }
            if result.correlation
            else None
        ),
        target_candidates=result.target_candidates,
        missingness_summary=result.missingness_summary,
    )

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload


@router.post("/regression", response_model=RegressionResult, status_code=status.HTTP_201_CREATED)
async def run_regression(
    payload: RegressionRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegressionResult:
    """Fit an OLS regression (target ~ features), persisting a Model row for later validation."""
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.REGRESSION,
        config=payload.model_dump(exclude={"dataset_id"}),
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    try:
        df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        fit = compute_regression(
            df, payload.target, payload.features, payload.log_target, payload.interactions
        )
    except RegressionError as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "regression_failed", str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "regression_failed", f"L'analyse a échoué : {exc}"
        ) from exc

    model_row = AnalysisModel(
        company_id=user.company_id,
        dataset_id=dataset.id,
        job_id=job.id,
        model_type="ols",
        config={
            "target": payload.target,
            "features": payload.features,
            "log_target": payload.log_target,
            "interactions": payload.interactions,
            "formula": fit.formula,
        },
        metrics={
            "r_squared": fit.r_squared,
            "adj_r_squared": fit.adj_r_squared,
            "f_statistic": fit.f_statistic,
            "f_p_value": fit.f_p_value,
            "aic": fit.aic,
            "bic": fit.bic,
            "n_observations": fit.n_observations,
        },
        fitted_at=datetime.now(timezone.utc),
    )
    db.add(model_row)
    await db.flush()

    result_payload = RegressionResult(
        dataset_id=dataset.id,
        model_id=model_row.id,
        formula=fit.formula,
        n_observations=fit.n_observations,
        r_squared=fit.r_squared,
        adj_r_squared=fit.adj_r_squared,
        f_statistic=fit.f_statistic,
        f_p_value=fit.f_p_value,
        aic=fit.aic,
        bic=fit.bic,
        coefficients=[
            {
                "term": c.term, "coefficient": c.coefficient, "std_error": c.std_error,
                "t_stat": c.t_stat, "p_value": c.p_value, "ci_lower": c.ci_lower,
                "ci_upper": c.ci_upper, "significant": c.significant,
                "interpretation": c.interpretation,
            }
            for c in fit.coefficients
        ],
        interpretation=fit.interpretation,
    )

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload


@router.post("/anova", response_model=ANOVAResult, status_code=status.HTTP_201_CREATED)
async def run_anova(
    payload: ANOVARequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ANOVAResult:
    """Run a one-way ANOVA of `response` across the groups of `factor`, with Tukey post-hoc."""
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.ANOVA,
        config=payload.model_dump(exclude={"dataset_id"}),
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    try:
        df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        fit = compute_anova(df, payload.factor, payload.response, payload.post_hoc)
    except ANOVAError as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "anova_failed", str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "anova_failed", f"L'analyse a échoué : {exc}"
        ) from exc

    result_payload = ANOVAResult(
        dataset_id=dataset.id,
        factor=fit.factor,
        response=fit.response,
        groups=fit.groups,
        ss_between=fit.ss_between,
        ss_within=fit.ss_within,
        df_between=fit.df_between,
        df_within=fit.df_within,
        ms_between=fit.ms_between,
        ms_within=fit.ms_within,
        f_statistic=fit.f_statistic,
        p_value=fit.p_value,
        eta_squared=fit.eta_squared,
        significant=fit.significant,
        tukey=[
            {
                "group1": t.group1, "group2": t.group2, "mean_diff": t.mean_diff,
                "p_adj": t.p_adj, "lower": t.lower, "upper": t.upper,
                "reject_null": t.reject_null,
            }
            for t in fit.tukey
        ],
        interpretation=fit.interpretation,
    )

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload


@router.post("/validation", response_model=ValidationResult, status_code=status.HTTP_201_CREATED)
async def run_model_validation(
    payload: ValidationRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValidationResult:
    """
    Run the mandatory six-test diagnostic suite on a previously fitted regression
    model (normality, heteroscedasticity, autocorrelation, multicollinearity,
    influence, plus residual plot data). Never report R² alone.
    """
    result = await db.execute(
        select(AnalysisModel).where(
            AnalysisModel.id == payload.model_id, AnalysisModel.company_id == user.company_id
        )
    )
    model_row = result.scalar_one_or_none()
    if model_row is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "model_not_found", "Modèle introuvable.")
    if model_row.model_type != "ols":
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "unsupported_model_type",
            "La suite de validation ne s'applique qu'aux modèles de régression OLS.",
        )

    dataset = await _get_owned_dataset(db, model_row.dataset_id, user.company_id)

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.VALIDATION,
        config={"model_id": str(model_row.id)},
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    try:
        df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        cfg = model_row.config
        suite = run_validation_suite(
            df,
            target=cfg["target"],
            features=cfg["features"],
            log_target=cfg.get("log_target", False),
            interactions=cfg.get("interactions"),
        )
    except ValidationError as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_failed", str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_failed", f"La validation a échoué : {exc}"
        ) from exc

    result_payload = ValidationResult(
        model_id=model_row.id,
        dataset_id=dataset.id,
        normality={
            "statistic": suite.normality.statistic, "p_value": suite.normality.p_value,
            "threshold": suite.normality.threshold, "verdict": suite.normality.verdict,
            "meaning": suite.normality.meaning,
        },
        qq_plot=suite.qq_plot,
        heteroscedasticity={
            "statistic": suite.heteroscedasticity.statistic, "p_value": suite.heteroscedasticity.p_value,
            "threshold": suite.heteroscedasticity.threshold, "verdict": suite.heteroscedasticity.verdict,
            "meaning": suite.heteroscedasticity.meaning,
        },
        autocorrelation={
            "statistic": suite.autocorrelation.statistic, "p_value": suite.autocorrelation.p_value,
            "threshold": suite.autocorrelation.threshold, "verdict": suite.autocorrelation.verdict,
            "meaning": suite.autocorrelation.meaning,
        },
        multicollinearity={
            "vif": [
                {"feature": v.feature, "vif": v.vif, "verdict": v.verdict} for v in suite.multicollinearity.vif
            ],
            "verdict": suite.multicollinearity.verdict,
            "meaning": suite.multicollinearity.meaning,
        },
        influence={
            "threshold": suite.influence.threshold, "influential_count": suite.influence.influential_count,
            "influential_ratio": suite.influence.influential_ratio,
            "influential_indices": suite.influence.influential_indices,
            "verdict": suite.influence.verdict, "meaning": suite.influence.meaning,
        },
        residual_vs_fitted=suite.residual_vs_fitted,
        residual_histogram=suite.residual_histogram,
        overall_verdict=suite.overall_verdict,
        remediation=suite.remediation,
    )

    # Fold the validation verdict into the persisted model's metrics for quick reference
    # elsewhere (e.g. the Decision Engine's confidence scoring in a later phase).
    model_row.metrics = {**model_row.metrics, "validation_overall_verdict": suite.overall_verdict}

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload


@router.post("/forecast", response_model=ForecastResult, status_code=status.HTTP_201_CREATED)
async def run_forecast(
    payload: ForecastRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ForecastResult:
    """
    Fit ARIMA and ETS on the dataset's daily-aggregated target, compare them on
    a holdout split, and forecast `horizon` future days with 80%/95% CI bands
    using the better-performing model.
    """
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.FORECAST,
        config=payload.model_dump(exclude={"dataset_id"}),
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    try:
        df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        fit = compute_forecast(
            df, payload.time_column, payload.target, payload.horizon, payload.train_split
        )
    except ForecastError as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "forecast_failed", str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "forecast_failed", f"La prévision a échoué : {exc}"
        ) from exc

    model_row = AnalysisModel(
        company_id=user.company_id,
        dataset_id=dataset.id,
        job_id=job.id,
        model_type=fit.best_model,
        config={
            "time_column": fit.time_column, "target": fit.target, "horizon": fit.horizon,
            "arima_order": list(fit.arima_order) if fit.arima_order else None,
            "ets_config": fit.ets_config,
        },
        metrics={
            "arima": {"mae": fit.arima_metrics.mae, "rmse": fit.arima_metrics.rmse, "mape": fit.arima_metrics.mape},
            "ets": {"mae": fit.ets_metrics.mae, "rmse": fit.ets_metrics.rmse, "mape": fit.ets_metrics.mape},
            "best_model": fit.best_model,
        },
        fitted_at=datetime.now(timezone.utc),
    )
    db.add(model_row)
    await db.flush()

    forecast_row = Forecast(
        model_id=model_row.id,
        horizon=fit.horizon,
        point={"dates": fit.forecast_dates, "values": fit.forecast_point},
        ci_lower={"80": fit.forecast_ci_lower_80, "95": fit.forecast_ci_lower_95},
        ci_upper={"80": fit.forecast_ci_upper_80, "95": fit.forecast_ci_upper_95},
        metrics=model_row.metrics,
    )
    db.add(forecast_row)
    await db.flush()

    result_payload = ForecastResult(
        dataset_id=dataset.id,
        model_id=model_row.id,
        forecast_id=forecast_row.id,
        time_column=fit.time_column,
        target=fit.target,
        horizon=fit.horizon,
        stationarity=[
            {"test": s.test, "statistic": s.statistic, "p_value": s.p_value, "verdict": s.verdict, "meaning": s.meaning}
            for s in fit.stationarity
        ],
        arima_order=list(fit.arima_order) if fit.arima_order else None,
        arima_metrics={"mae": fit.arima_metrics.mae, "rmse": fit.arima_metrics.rmse, "mape": fit.arima_metrics.mape},
        ets_config=fit.ets_config,
        ets_metrics={"mae": fit.ets_metrics.mae, "rmse": fit.ets_metrics.rmse, "mape": fit.ets_metrics.mape},
        best_model=fit.best_model,
        history={"dates": fit.history_dates, "actual": fit.history_actual, "fitted": fit.history_fitted},
        forecast={
            "dates": fit.forecast_dates, "point": fit.forecast_point,
            "ci_lower_80": fit.forecast_ci_lower_80, "ci_upper_80": fit.forecast_ci_upper_80,
            "ci_lower_95": fit.forecast_ci_lower_95, "ci_upper_95": fit.forecast_ci_upper_95,
        },
        interpretation=fit.interpretation,
    )

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload


@router.post("/segmentation", response_model=SegmentationResult, status_code=status.HTTP_201_CREATED)
async def run_segmentation(
    payload: SegmentationRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SegmentationResult:
    """Cluster customers/rows via K-Means (auto-k) or DBSCAN, with a PCA projection for plotting."""
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.SEGMENTATION,
        config=payload.model_dump(exclude={"dataset_id"}),
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    try:
        df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        fit = compute_segmentation(
            df, payload.features, payload.algorithm, payload.k_min, payload.k_max
        )
    except SegmentationError as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "segmentation_failed", str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "segmentation_failed", f"La segmentation a échoué : {exc}"
        ) from exc

    segment_row = Segment(
        company_id=user.company_id,
        dataset_id=dataset.id,
        algorithm=fit.algorithm,
        n_clusters=fit.n_clusters,
        features={"columns": payload.features},
        silhouette=fit.silhouette,
        centroids=fit.centroids,
    )
    db.add(segment_row)
    await db.flush()

    result_payload = SegmentationResult(
        segment_id=segment_row.id,
        dataset_id=dataset.id,
        algorithm=fit.algorithm,
        n_clusters=fit.n_clusters,
        silhouette=fit.silhouette,
        elbow=[{"k": e.k, "inertia": e.inertia, "silhouette": e.silhouette} for e in fit.elbow],
        clusters=[
            {
                "cluster": c.cluster, "name": c.name, "size": c.size,
                "share": c.share, "feature_means": c.feature_means,
            }
            for c in fit.clusters
        ],
        pca_explained_variance=fit.pca_explained_variance,
        pca_points=[{"x": p.x, "y": p.y, "cluster": p.cluster} for p in fit.pca_points],
        centroids=fit.centroids,
        interpretation=fit.interpretation,
    )

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload

@router.post("/kpis", response_model=KPISuiteResult, status_code=status.HTTP_201_CREATED)
async def run_kpis(
    payload: KPIRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KPISuiteResult:
    """
    Compute the business KPI suite (CLTV, Churn, Take Rate, CAC, WOM, Revenue
    Growth, Gross Margin), plus AOV/repeat-purchase supporting metrics. KPIs
    whose required columns weren't supplied come back as "insufficient_data"
    rather than failing the whole request.
    """
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.KPI,
        config=payload.model_dump(exclude={"dataset_id"}),
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    try:
        df = read_dataset_file(dataset.storage_path, dataset.file_type.value)
        fit = compute_kpi_suite(
            df,
            date_column=payload.date_column,
            customer_id_column=payload.customer_id_column,
            revenue_column=payload.revenue_column,
            quantity_column=payload.quantity_column,
            price_column=payload.price_column,
            cost_column=payload.cost_column,
            marketing_spend_column=payload.marketing_spend_column,
            fee_column=payload.fee_column,
            commission_rate=payload.commission_rate,
            nps_column=payload.nps_column,
        )
    except Exception as exc:  # pragma: no cover - defensive
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "kpi_failed", f"Le calcul des KPI a échoué : {exc}"
        ) from exc

    now = datetime.now(timezone.utc)
    for item in fit.kpis:
        if item.status == "computed" and item.value is not None:
            db.add(
                KPI(
                    company_id=user.company_id,
                    dataset_id=dataset.id,
                    kpi_type=KPIType(item.kpi_type),
                    value=item.value,
                    formula=item.formula,
                    computed_at=now,
                )
            )

    result_payload = KPISuiteResult(
        dataset_id=dataset.id,
        kpis=[
            {
                "kpi_type": k.kpi_type, "status": k.status, "value": k.value, "formula": k.formula,
                "data_coverage": {
                    "rows_used": k.data_coverage.rows_used, "rows_total": k.data_coverage.rows_total,
                    "coverage_ratio": k.data_coverage.coverage_ratio,
                },
                "missing": k.missing,
                "trend": ({"direction": k.trend.direction, "change_pct": k.trend.change_pct} if k.trend else None),
                "interpretation": k.interpretation,
                "extra": k.extra,
            }
            for k in fit.kpis
        ],
        supporting_metrics=[
            {"name": s.name, "value": s.value, "formula": s.formula, "status": s.status}
            for s in fit.supporting_metrics
        ],
        interpretation=fit.interpretation,
    )

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload


async def _latest_completed_result(
    db: AsyncSession, dataset_id: UUID, company_id: UUID, job_type: JobType
) -> Optional[dict]:
    result = await db.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.dataset_id == dataset_id,
            AnalysisJob.company_id == company_id,
            AnalysisJob.type == job_type,
            AnalysisJob.status == JobStatus.COMPLETED,
        )
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    return job.result if job else None


@router.post("/decision", response_model=DecisionGenerateResult, status_code=status.HTTP_201_CREATED)
async def run_decision_engine(
    payload: DecisionGenerateRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DecisionGenerateResult:
    """
    Generate prioritized, evidence-backed recommendations from the dataset's
    most recent completed analyses (regression, validation, forecast,
    segmentation, kpi). Persists each recommendation as a `decisions` row.
    """
    dataset = await _get_owned_dataset(db, payload.dataset_id, user.company_id)

    ctx = DecisionContext(
        regression=await _latest_completed_result(db, dataset.id, user.company_id, JobType.REGRESSION),
        validation=await _latest_completed_result(db, dataset.id, user.company_id, JobType.VALIDATION),
        forecast=await _latest_completed_result(db, dataset.id, user.company_id, JobType.FORECAST),
        segmentation=await _latest_completed_result(db, dataset.id, user.company_id, JobType.SEGMENTATION),
        kpi=await _latest_completed_result(db, dataset.id, user.company_id, JobType.KPI),
    )

    job = AnalysisJob(
        company_id=user.company_id,
        dataset_id=dataset.id,
        type=JobType.DECISION,
        config={},
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    candidates = generate_decisions(ctx)

    decision_rows = []
    for c in candidates:
        row = Decision(
            company_id=user.company_id,
            dataset_id=dataset.id,
            source_job_id=job.id,
            priority=DecisionPriority(c.priority),
            category=c.category,
            title=c.title,
            description=c.description,
            evidence=c.evidence,
            recommended_action=c.recommended_action,
            status=DecisionStatusModel.OPEN,
        )
        db.add(row)
        decision_rows.append(row)
    await db.flush()

    result_payload = DecisionGenerateResult(
        dataset_id=dataset.id,
        decisions=[
            {
                "id": row.id, "priority": row.priority.value, "category": row.category,
                "title": row.title, "description": row.description, "evidence": row.evidence,
                "recommended_action": row.recommended_action,
                "confidence": row.evidence.get("confidence", "medium"),
                "status": row.status.value,
            }
            for row in decision_rows
        ],
    )

    job.status = JobStatus.COMPLETED
    job.progress = 100.0
    job.result = result_payload.model_dump(mode="json")
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return result_payload
