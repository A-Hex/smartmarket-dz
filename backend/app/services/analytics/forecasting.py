# backend/app/services/analytics/forecasting.py
"""
Demand Forecasting engine (ARIMA + ETS).

Pure function of (DataFrame, time_column, target, horizon, train_split) ->
ForecastFitResult. The raw transaction-level dataset is aggregated to one
observation per calendar day (sum of target), which is the standard framing
for demand forecasting on retail data.

Both models are:
  1. fit on the training split only, and scored on the held-out test split
     (MAE / RMSE / MAPE) so the two approaches are fairly compared;
  2. then refit on the *entire* series to produce the actual future-horizon
     forecast with 80%/95% confidence intervals.
"""
import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.stattools import adfuller, kpss

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


class ForecastError(ValueError):
    """Raised when the requested forecast cannot be computed."""


@dataclass
class StationarityTest:
    test: str
    statistic: float
    p_value: float
    verdict: str  # "stationary" | "non_stationary"
    meaning: str


@dataclass
class ForecastMetrics:
    mae: float
    rmse: float
    mape: float


@dataclass
class ForecastFitResult:
    time_column: str
    target: str
    horizon: int
    stationarity: list[StationarityTest]
    arima_order: Optional[tuple]
    arima_metrics: ForecastMetrics
    ets_config: Optional[dict]
    ets_metrics: ForecastMetrics
    best_model: str
    history_dates: list
    history_actual: list
    history_fitted: list
    forecast_dates: list
    forecast_point: list
    forecast_ci_lower_80: list
    forecast_ci_upper_80: list
    forecast_ci_lower_95: list
    forecast_ci_upper_95: list
    interpretation: str = ""


def _build_daily_series(df: pd.DataFrame, time_column: str, target: str) -> pd.Series:
    if time_column not in df.columns or target not in df.columns:
        missing = [c for c in [time_column, target] if c not in df.columns]
        raise ForecastError(f"Colonnes inconnues : {', '.join(missing)}")

    working = df[[time_column, target]].copy()
    working[time_column] = pd.to_datetime(working[time_column], errors="coerce")
    working[target] = pd.to_numeric(working[target], errors="coerce")
    working = working.dropna()

    if working.empty:
        raise ForecastError("Aucune observation valide (date + valeur numérique) pour la prévision.")

    daily = working.groupby(working[time_column].dt.floor("D"))[target].sum().sort_index()
    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full_index, fill_value=0.0)
    daily.index.name = time_column

    if len(daily) < 20:
        raise ForecastError(
            "Serie temporelle trop courte pour une prevision fiable (minimum 20 points requis)."
        )
    return daily


def _stationarity_tests(series: pd.Series) -> list:
    adf_stat, adf_p, *_ = adfuller(series, autolag="AIC")
    adf_verdict = "stationary" if adf_p < 0.05 else "non_stationary"
    adf = StationarityTest(
        test="adf", statistic=float(adf_stat), p_value=float(adf_p), verdict=adf_verdict,
        meaning=(
            f"Test ADF : p={adf_p:.4f}. "
            + ("La serie est stationnaire (H0 rejetee)." if adf_verdict == "stationary"
               else "La serie n'est pas stationnaire (H0 non rejetee) ; une differenciation peut etre necessaire.")
        ),
    )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            kpss_stat, kpss_p, *_ = kpss(series, regression="c", nlags="auto")
        kpss_verdict = "non_stationary" if kpss_p < 0.05 else "stationary"
        kpss_test = StationarityTest(
            test="kpss", statistic=float(kpss_stat), p_value=float(kpss_p), verdict=kpss_verdict,
            meaning=(
                f"Test KPSS : p={kpss_p:.4f}. "
                + ("La serie n'est pas stationnaire (H0 rejetee)." if kpss_verdict == "non_stationary"
                   else "La serie est stationnaire (H0 non rejetee).")
            ),
        )
    except Exception:
        kpss_test = StationarityTest(
            test="kpss", statistic=float("nan"), p_value=float("nan"), verdict="stationary",
            meaning="Test KPSS non calculable pour cette serie ; resultat ADF utilise seul.",
        )

    return [adf, kpss_test]


def _metrics(actual, predicted) -> ForecastMetrics:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    errors = actual - predicted
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    nonzero_mask = np.abs(actual) > 1e-9
    if nonzero_mask.any():
        mape = float(np.mean(np.abs(errors[nonzero_mask] / actual[nonzero_mask])) * 100)
    else:
        mape = float("nan")
    return ForecastMetrics(mae=mae, rmse=rmse, mape=mape)


def _fit_arima(train: pd.Series, test_len: int):
    """Fit via pmdarima.auto_arima (AIC-selected, p,d,q capped at 5,2,5)."""
    import pmdarima as pm

    model = pm.auto_arima(
        train.values,
        start_p=0, start_q=0, max_p=5, max_d=2, max_q=5,
        seasonal=False, stepwise=True, suppress_warnings=True,
        error_action="ignore", information_criterion="aic",
    )
    order = model.order
    test_forecast = model.predict(n_periods=test_len)
    return model, order, np.asarray(test_forecast)


def _fit_ets(train: pd.Series, test_len: int):
    """
    Approximate 'auto' ETS selection: try a small grid of trend/damped configs
    (statsmodels has no built-in auto-ETS like R's ets()), pick lowest AIC on train.
    Additive seasonal is skipped since the daily aggregation has no reliably known period.
    """
    candidates = [
        {"trend": None, "damped_trend": False},
        {"trend": "add", "damped_trend": False},
        {"trend": "add", "damped_trend": True},
    ]
    best = None
    best_aic = float("inf")
    best_cfg = None

    for cfg in candidates:
        try:
            model = ETSModel(train, error="add", trend=cfg["trend"],
                              damped_trend=cfg["damped_trend"], seasonal=None)
            fitted = model.fit(disp=False)
            if fitted.aic < best_aic:
                best_aic = fitted.aic
                best = fitted
                best_cfg = cfg
        except Exception:
            continue

    if best is None:
        raise ForecastError("Impossible d'ajuster un modele ETS sur cette serie.")

    test_forecast = best.forecast(test_len)
    return best, best_cfg, np.asarray(test_forecast)


def compute_forecast(
    df: pd.DataFrame, time_column: str, target: str, horizon: int = 12, train_split: float = 0.8
) -> ForecastFitResult:
    """Fit ARIMA and ETS, compare on a holdout split, then forecast `horizon` future days."""
    series = _build_daily_series(df, time_column, target)
    stationarity = _stationarity_tests(series)

    n = len(series)
    split_idx = int(n * train_split)
    split_idx = min(split_idx, n - 5)
    split_idx = max(split_idx, 5)

    if split_idx >= n:
        raise ForecastError("Pas assez de donnees pour creer un ensemble d'entrainement/test.")

    train, test = series.iloc[:split_idx], series.iloc[split_idx:]

    try:
        _arima_model, arima_order, arima_test_pred = _fit_arima(train, len(test))
        arima_metrics = _metrics(test.values, arima_test_pred)
    except Exception:
        arima_order = None
        arima_metrics = ForecastMetrics(mae=float("inf"), rmse=float("inf"), mape=float("inf"))

    try:
        _ets_fitted, ets_cfg, ets_test_pred = _fit_ets(train, len(test))
        ets_metrics = _metrics(test.values, ets_test_pred)
    except Exception:
        ets_cfg = None
        ets_metrics = ForecastMetrics(mae=float("inf"), rmse=float("inf"), mape=float("inf"))

    if arima_metrics.rmse == float("inf") and ets_metrics.rmse == float("inf"):
        raise ForecastError("Ni ARIMA ni ETS n'ont pu etre ajustes sur cette serie.")

    best_model = "arima" if arima_metrics.rmse <= ets_metrics.rmse else "ets"

    forecast_index = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")

    if best_model == "arima":
        import pmdarima as pm

        full_model = pm.auto_arima(
            series.values, start_p=0, start_q=0, max_p=5, max_d=2, max_q=5,
            seasonal=False, stepwise=True, suppress_warnings=True, error_action="ignore",
        )
        arima_order = full_model.order
        point_80, ci_80 = full_model.predict(n_periods=horizon, return_conf_int=True, alpha=0.20)
        _point_95, ci_95 = full_model.predict(n_periods=horizon, return_conf_int=True, alpha=0.05)
        point = np.asarray(point_80)
        ci_lower_80, ci_upper_80 = ci_80[:, 0], ci_80[:, 1]
        ci_lower_95, ci_upper_95 = ci_95[:, 0], ci_95[:, 1]
        history_fitted = full_model.predict_in_sample()
    else:
        full_model = ETSModel(
            series, error="add",
            trend=ets_cfg["trend"] if ets_cfg else None,
            damped_trend=ets_cfg["damped_trend"] if ets_cfg else False,
            seasonal=None,
        )
        full_fitted = full_model.fit(disp=False)
        pred = full_fitted.get_prediction(start=len(series), end=len(series) + horizon - 1)
        summary_80 = pred.summary_frame(alpha=0.20)
        summary_95 = pred.summary_frame(alpha=0.05)
        point = summary_80["mean"].values
        ci_lower_80, ci_upper_80 = summary_80["pi_lower"].values, summary_80["pi_upper"].values
        ci_lower_95, ci_upper_95 = summary_95["pi_lower"].values, summary_95["pi_upper"].values
        history_fitted = full_fitted.fittedvalues.values

    winner_metrics = arima_metrics if best_model == "arima" else ets_metrics
    loser_name = "ETS" if best_model == "arima" else "ARIMA"
    interpretation = (
        f"Le modele {'ARIMA' if best_model == 'arima' else 'ETS'} offre la meilleure precision sur "
        f"l'ensemble de test (RMSE={winner_metrics.rmse:.2f}, MAE={winner_metrics.mae:.2f}, "
        f"MAPE={winner_metrics.mape:.1f}%), et est recommande pour la prevision sur {horizon} jours. "
        f"Le modele {loser_name} a ete moins precis sur cette periode."
    )

    return ForecastFitResult(
        time_column=time_column,
        target=target,
        horizon=horizon,
        stationarity=stationarity,
        arima_order=tuple(int(x) for x in arima_order) if arima_order else None,
        arima_metrics=arima_metrics,
        ets_config=ets_cfg,
        ets_metrics=ets_metrics,
        best_model=best_model,
        history_dates=[d.strftime("%Y-%m-%d") for d in series.index],
        history_actual=[float(v) for v in series.values],
        history_fitted=[
            (float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else None)
            for v in history_fitted
        ],
        forecast_dates=[d.strftime("%Y-%m-%d") for d in forecast_index],
        forecast_point=[float(v) for v in point],
        forecast_ci_lower_80=[float(v) for v in ci_lower_80],
        forecast_ci_upper_80=[float(v) for v in ci_upper_80],
        forecast_ci_lower_95=[float(v) for v in ci_lower_95],
        forecast_ci_upper_95=[float(v) for v in ci_upper_95],
        interpretation=interpretation,
    )
