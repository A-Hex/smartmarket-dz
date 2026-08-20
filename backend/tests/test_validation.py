# backend/tests/test_validation.py
"""
Unit tests for app.services.analytics.validation.

Per the spec's testing requirements: validation suite verdicts must be checked
against synthetic datasets with known properties - e.g. heteroscedastic data
must FAIL Breusch-Pagan, and collinear features must FAIL the VIF check.
"""
import numpy as np
import pandas as pd
import pytest

from app.services.analytics.validation import ValidationError, run_validation_suite


def test_well_behaved_linear_model_passes_most_tests():
    rng = np.random.default_rng(1)
    n = 300
    x1 = rng.uniform(0, 100, n)
    x2 = rng.uniform(0, 100, n)
    y = 10 + 2 * x1 + 0.5 * x2 + rng.normal(0, 5, n)
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})

    suite = run_validation_suite(df, target="y", features=["x1", "x2"])

    assert suite.multicollinearity.verdict == "pass"
    assert suite.heteroscedasticity.verdict in ("pass", "warn")
    assert suite.overall_verdict in ("pass", "warn")
    assert len(suite.multicollinearity.vif) == 2


def test_heteroscedastic_data_fails_breusch_pagan():
    rng = np.random.default_rng(2)
    n = 400
    x = rng.uniform(1, 100, n)
    noise = rng.normal(0, 1, n) * x
    y = 5 + 2 * x + noise
    df = pd.DataFrame({"x": x, "y": y})

    suite = run_validation_suite(df, target="y", features=["x"])

    assert suite.heteroscedasticity.verdict in ("warn", "fail")
    assert suite.heteroscedasticity.p_value is not None
    assert suite.heteroscedasticity.p_value < 0.05


def test_collinear_features_fail_vif():
    rng = np.random.default_rng(3)
    n = 300
    x1 = rng.uniform(0, 1000, n)
    x2 = x1 * 0.98 + rng.normal(0, 1, n)
    y = 3 * x1 + rng.normal(0, 50, n)
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})

    suite = run_validation_suite(df, target="y", features=["x1", "x2"])

    assert suite.multicollinearity.verdict == "fail"
    failing_features = {v.feature for v in suite.multicollinearity.vif if v.verdict == "fail"}
    assert failing_features
    assert suite.overall_verdict == "fail"
    assert any("multicolin" in r.lower() or "corrélées" in r.lower() for r in suite.remediation)


def test_validation_includes_all_six_components():
    rng = np.random.default_rng(4)
    n = 100
    x = rng.uniform(0, 10, n)
    y = 2 * x + rng.normal(0, 1, n)
    df = pd.DataFrame({"x": x, "y": y})

    suite = run_validation_suite(df, target="y", features=["x"])

    assert suite.normality is not None
    assert suite.heteroscedasticity is not None
    assert suite.autocorrelation is not None
    assert suite.multicollinearity is not None
    assert suite.influence is not None
    assert "fitted" in suite.residual_vs_fitted and "residuals" in suite.residual_vs_fitted
    assert "bin_edges" in suite.residual_histogram and "counts" in suite.residual_histogram
    assert suite.overall_verdict in ("pass", "warn", "fail")


def test_validation_raises_on_bad_regression_config():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 2, 3]})
    with pytest.raises(ValidationError):
        run_validation_suite(df, target="y", features=["does_not_exist"])


def test_durbin_watson_zone_reported():
    rng = np.random.default_rng(5)
    n = 200
    x = rng.uniform(0, 10, n)
    y = 2 * x + rng.normal(0, 1, n)
    df = pd.DataFrame({"x": x, "y": y})
    suite = run_validation_suite(df, target="y", features=["x"])
    assert 0 <= suite.autocorrelation.statistic <= 4
    assert suite.autocorrelation.verdict in ("pass", "warn", "fail")
