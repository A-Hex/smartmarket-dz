# backend/app/schemas/analytics.py
"""Pydantic v2 schemas for analytics job configs and results.
Phase 4: descriptive stats. Phase 5: regression (OLS) + ANOVA.
"""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DescriptiveRequest(BaseModel):
    """Config for POST /analytics/descriptive. Empty columns list = profile every column."""

    dataset_id: UUID
    columns: list[str] = Field(default_factory=list)


class NumericColumnStats(BaseModel):
    column: str
    count: int
    missing: int
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[float] = None
    variance: Optional[float] = None
    std: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    iqr: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    interpretation: str


class CategoricalColumnStats(BaseModel):
    column: str
    count: int
    missing: int
    unique: int
    frequency_table: dict[str, int]
    interpretation: str


class CorrelationMatrix(BaseModel):
    columns: list[str]
    pearson: list[list[Optional[float]]]
    spearman: list[list[Optional[float]]]


class DescriptiveResult(BaseModel):
    dataset_id: UUID
    row_count: int
    numeric_columns: list[NumericColumnStats]
    categorical_columns: list[CategoricalColumnStats]
    correlation: Optional[CorrelationMatrix] = None
    target_candidates: list[str]
    missingness_summary: dict[str, int]


# --- Phase 5: Regression (OLS) -----------------------------------------


class RegressionRequest(BaseModel):
    """Config for POST /analytics/regression."""

    dataset_id: UUID
    target: str
    features: list[str] = Field(min_length=1)
    log_target: bool = Field(default=False, description="Fit log(target) ~ features")
    interactions: list[list[str]] = Field(
        default_factory=list,
        description="Pairs of feature names to include as interaction terms, e.g. [['price','region']]",
    )


class CoefficientResult(BaseModel):
    term: str
    coefficient: float
    std_error: float
    t_stat: float
    p_value: float
    ci_lower: float
    ci_upper: float
    significant: bool
    interpretation: str


class RegressionResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    dataset_id: UUID
    model_id: UUID
    formula: str
    n_observations: int
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_p_value: float
    aic: float
    bic: float
    coefficients: list[CoefficientResult]
    interpretation: str


# --- Phase 5: ANOVA -------------------------------------------------------


class ANOVARequest(BaseModel):
    """Config for POST /analytics/anova (one-way)."""

    dataset_id: UUID
    factor: str
    response: str
    post_hoc: bool = True


class TukeyPairResult(BaseModel):
    group1: str
    group2: str
    mean_diff: float
    p_adj: float
    lower: float
    upper: float
    reject_null: bool


class ANOVAResult(BaseModel):
    dataset_id: UUID
    factor: str
    response: str
    groups: list[str]
    ss_between: float
    ss_within: float
    df_between: int
    df_within: int
    ms_between: float
    ms_within: float
    f_statistic: float
    p_value: float
    eta_squared: float
    significant: bool
    tukey: list[TukeyPairResult]
    interpretation: str


# --- Phase 6: Model Validation suite --------------------------------------


class ValidationRequest(BaseModel):
    """Config for POST /analytics/validation. Runs the six-test suite on a fitted model."""

    model_config = ConfigDict(protected_namespaces=())

    model_id: UUID


class TestResultRead(BaseModel):
    statistic: float
    p_value: Optional[float] = None
    threshold: str
    verdict: str  # "pass" | "warn" | "fail"
    meaning: str


class VIFResultRead(BaseModel):
    feature: str
    vif: float
    verdict: str


class MulticollinearityResultRead(BaseModel):
    vif: list[VIFResultRead]
    verdict: str
    meaning: str


class InfluenceResultRead(BaseModel):
    threshold: float
    influential_count: int
    influential_ratio: float
    influential_indices: list[int]
    verdict: str
    meaning: str


class ValidationResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: UUID
    dataset_id: UUID
    normality: TestResultRead
    qq_plot: dict[str, list[float]]
    heteroscedasticity: TestResultRead
    autocorrelation: TestResultRead
    multicollinearity: MulticollinearityResultRead
    influence: InfluenceResultRead
    residual_vs_fitted: dict[str, list[float]]
    residual_histogram: dict[str, list[float]]
    overall_verdict: str
    remediation: list[str]


# --- Phase 7: Demand Forecasting (ARIMA + ETS) -----------------------------


class ForecastRequest(BaseModel):
    """Config for POST /analytics/forecast."""

    dataset_id: UUID
    time_column: str
    target: str
    horizon: int = Field(default=12, ge=1, le=365)
    train_split: float = Field(default=0.8, gt=0.5, lt=1.0)


class StationarityTestRead(BaseModel):
    test: str  # "adf" | "kpss"
    statistic: float
    p_value: float
    verdict: str  # "stationary" | "non_stationary"
    meaning: str


class ForecastMetricsRead(BaseModel):
    mae: float
    rmse: float
    mape: float


class ForecastSeriesRead(BaseModel):
    dates: list[str]
    actual: list[Optional[float]]
    fitted: list[Optional[float]]


class ForecastPointsRead(BaseModel):
    dates: list[str]
    point: list[float]
    ci_lower_80: list[float]
    ci_upper_80: list[float]
    ci_lower_95: list[float]
    ci_upper_95: list[float]


class ForecastResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    dataset_id: UUID
    model_id: UUID
    forecast_id: UUID
    time_column: str
    target: str
    horizon: int
    stationarity: list[StationarityTestRead]
    arima_order: Optional[list[int]] = None
    arima_metrics: ForecastMetricsRead
    ets_config: Optional[dict[str, Any]] = None
    ets_metrics: ForecastMetricsRead
    best_model: str  # "arima" | "ets"
    history: ForecastSeriesRead
    forecast: ForecastPointsRead
    interpretation: str


# --- Phase 7: Customer Segmentation (K-Means / DBSCAN + PCA) --------------


class SegmentationRequest(BaseModel):
    dataset_id: UUID
    features: list[str] = Field(min_length=2)
    algorithm: str = Field(default="kmeans", pattern="^(kmeans|dbscan)$")
    k_min: int = Field(default=2, ge=2)
    k_max: int = Field(default=10, ge=2, le=20)


class ClusterProfileRead(BaseModel):
    cluster: int
    name: str
    size: int
    share: float
    feature_means: dict[str, float]


class PCAPointRead(BaseModel):
    x: float
    y: float
    cluster: int


class ElbowPointRead(BaseModel):
    k: int
    inertia: float
    silhouette: Optional[float] = None


class SegmentationResult(BaseModel):
    segment_id: UUID
    dataset_id: UUID
    algorithm: str
    n_clusters: Optional[int] = None
    silhouette: Optional[float] = None
    elbow: list[ElbowPointRead]
    clusters: list[ClusterProfileRead]
    pca_explained_variance: list[float]
    pca_points: list[PCAPointRead]
    centroids: dict[str, Any]
    interpretation: str


# --- Phase 8: KPI Engine ---------------------------------------------------


class KPIRequest(BaseModel):
    """
    Config for POST /analytics/kpis. All column mappings are optional — KPIs
    whose required columns aren't supplied are returned with
    status="insufficient_data" rather than failing the whole request.
    """

    dataset_id: UUID
    date_column: Optional[str] = None
    customer_id_column: Optional[str] = None
    revenue_column: Optional[str] = None
    quantity_column: Optional[str] = None
    price_column: Optional[str] = None
    cost_column: Optional[str] = None
    marketing_spend_column: Optional[str] = None
    fee_column: Optional[str] = Field(
        default=None, description="Per-row platform commission/fee amount, for Take Rate."
    )
    commission_rate: Optional[float] = Field(
        default=None, description="Flat commission rate (0-1), alternative to fee_column."
    )
    nps_column: Optional[str] = Field(default=None, description="Survey/NPS-like score column, for WOM.")


class KPITrendRead(BaseModel):
    direction: str  # "up" | "down" | "flat"
    change_pct: Optional[float] = None


class KPIDataCoverageRead(BaseModel):
    rows_used: int
    rows_total: int
    coverage_ratio: float


class KPIItemResult(BaseModel):
    kpi_type: str
    status: str  # "computed" | "insufficient_data"
    value: Optional[float] = None
    formula: str
    data_coverage: KPIDataCoverageRead
    missing: list[str] = Field(default_factory=list)
    trend: Optional[KPITrendRead] = None
    interpretation: str
    extra: Optional[dict[str, Any]] = None


class KPISupportingMetricRead(BaseModel):
    name: str
    value: Optional[float] = None
    formula: str
    status: str


class KPISuiteResult(BaseModel):
    dataset_id: UUID
    kpis: list[KPIItemResult]
    supporting_metrics: list[KPISupportingMetricRead]
    interpretation: str


# --- Phase 8: Decision Engine ----------------------------------------------


class DecisionGenerateRequest(BaseModel):
    """Config for POST /analytics/decision. Pulls from the dataset's most recent completed jobs."""

    dataset_id: UUID


class DecisionRead(BaseModel):
    id: UUID
    priority: str
    category: str
    title: str
    description: str
    evidence: dict[str, Any]
    recommended_action: str
    confidence: str
    status: str


class DecisionGenerateResult(BaseModel):
    dataset_id: UUID
    decisions: list[DecisionRead]
