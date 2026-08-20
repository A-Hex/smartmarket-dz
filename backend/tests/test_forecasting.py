# backend/tests/test_forecasting.py
"""Unit tests for app.services.analytics.forecasting."""
import numpy as np
import pandas as pd
import pytest

from app.services.analytics.forecasting import ForecastError, compute_forecast


def _trending_series(n=120, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    trend = np.linspace(100, 300, n)
    noise = rng.normal(0, 10, n)
    values = trend + noise
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "sales": values})


def test_forecast_returns_both_models_and_picks_a_winner():
    df = _trending_series()
    result = compute_forecast(df, time_column="date", target="sales", horizon=14, train_split=0.8)

    assert result.best_model in ("arima", "ets")
    assert result.arima_metrics.rmse >= 0
    assert result.ets_metrics.rmse >= 0
    assert len(result.forecast_point) == 14
    assert len(result.forecast_dates) == 14
    assert len(result.forecast_ci_lower_80) == 14
    assert len(result.forecast_ci_upper_95) == 14
    # 95% CI should generally be wider than 80% CI
    for lo80, lo95, hi80, hi95 in zip(
        result.forecast_ci_lower_80, result.forecast_ci_lower_95,
        result.forecast_ci_upper_80, result.forecast_ci_upper_95,
    ):
        assert lo95 <= lo80
        assert hi95 >= hi80


def test_forecast_includes_stationarity_tests():
    df = _trending_series()
    result = compute_forecast(df, time_column="date", target="sales", horizon=7)
    test_names = {s.test for s in result.stationarity}
    assert test_names == {"adf", "kpss"}
    for s in result.stationarity:
        assert s.verdict in ("stationary", "non_stationary")


def test_forecast_aggregates_multiple_rows_per_day():
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    rows = []
    rng = np.random.default_rng(2)
    for d in dates:
        for _ in range(3):  # multiple transactions per day
            rows.append({"date": d.strftime("%Y-%m-%d"), "sales": rng.uniform(10, 20)})
    df = pd.DataFrame(rows)

    result = compute_forecast(df, time_column="date", target="sales", horizon=5)
    # aggregated to one point per day
    assert len(result.history_dates) == 40


def test_forecast_unknown_column_raises():
    df = _trending_series()
    with pytest.raises(ForecastError):
        compute_forecast(df, time_column="nope", target="sales", horizon=5)


def test_forecast_too_short_series_raises():
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5), "sales": [1, 2, 3, 4, 5]})
    with pytest.raises(ForecastError):
        compute_forecast(df, time_column="date", target="sales", horizon=3)
