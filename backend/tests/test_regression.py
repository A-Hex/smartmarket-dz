# backend/tests/test_regression.py
"""Unit tests for app.services.analytics.regression (pure functions)."""
import numpy as np
import pandas as pd
import pytest

from app.services.analytics.regression import RegressionError, compute_regression


def _make_linear_dataset(n=200, seed=7):
    rng = np.random.default_rng(seed)
    marketing = rng.uniform(100, 5000, n)
    price = rng.uniform(1000, 50000, n)
    noise = rng.normal(0, 200, n)
    sales = 500 + 3.0 * marketing - 0.02 * price + noise
    return pd.DataFrame({"marketing_spend": marketing, "price": price, "sales": sales})


def test_regression_recovers_known_significant_effect():
    df = _make_linear_dataset()
    result = compute_regression(df, target="sales", features=["marketing_spend", "price"])

    assert result.n_observations == 200
    assert result.r_squared > 0.9  # strong synthetic linear relationship

    marketing_term = next(c for c in result.coefficients if "marketing_spend" in c.term)
    assert marketing_term.coefficient > 0
    assert marketing_term.significant is True
    assert marketing_term.p_value < 0.05


def test_regression_unknown_column_raises():
    df = _make_linear_dataset()
    with pytest.raises(RegressionError):
        compute_regression(df, target="sales", features=["does_not_exist"])


def test_regression_with_log_target():
    df = _make_linear_dataset()
    df["sales"] = df["sales"].abs() + 1  # ensure positivity for log
    result = compute_regression(df, target="sales", features=["marketing_spend"], log_target=True)
    assert "np.log1p" in result.formula
    assert result.n_observations == 200


def test_regression_negative_log_target_rejected():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [-1, -2, 3, 4, 5]})
    with pytest.raises(RegressionError):
        compute_regression(df, target="y", features=["x"], log_target=True)


def test_regression_interpretation_present_for_every_coefficient():
    df = _make_linear_dataset()
    result = compute_regression(df, target="sales", features=["marketing_spend", "price"])
    for c in result.coefficients:
        assert c.interpretation
        assert isinstance(c.interpretation, str)
