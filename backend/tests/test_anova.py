# backend/tests/test_anova.py
"""Unit tests for app.services.analytics.anova (pure functions)."""
import numpy as np
import pandas as pd
import pytest

from app.services.analytics.anova import ANOVAError, compute_anova


def _make_three_group_dataset(seed=3):
    rng = np.random.default_rng(seed)
    # Deliberately well-separated group means so the F-test is unambiguously significant.
    alger = rng.normal(1000, 50, 40)
    oran = rng.normal(1400, 50, 40)
    constantine = rng.normal(1800, 50, 40)
    region = ["Alger"] * 40 + ["Oran"] * 40 + ["Constantine"] * 40
    sales = np.concatenate([alger, oran, constantine])
    return pd.DataFrame({"region": region, "sales": sales})


def test_anova_detects_significant_group_difference_with_tukey():
    df = _make_three_group_dataset()
    result = compute_anova(df, factor="region", response="sales")

    assert result.significant is True
    assert result.p_value < 0.05
    assert set(result.groups) == {"Alger", "Oran", "Constantine"}
    assert len(result.tukey) == 3  # 3 choose 2 pairs
    assert all(t.reject_null for t in result.tukey)  # all means are well-separated


def test_anova_no_difference_when_groups_are_identical_distribution():
    rng = np.random.default_rng(11)
    a = rng.normal(500, 50, 30)
    b = rng.normal(500, 50, 30)
    df = pd.DataFrame({"grp": ["A"] * 30 + ["B"] * 30, "val": np.concatenate([a, b])})
    result = compute_anova(df, factor="grp", response="val")
    assert result.f_statistic >= 0
    assert 0 <= result.p_value <= 1


def test_anova_unknown_columns_raise():
    df = _make_three_group_dataset()
    with pytest.raises(ANOVAError):
        compute_anova(df, factor="nope", response="sales")


def test_anova_single_group_raises():
    df = pd.DataFrame({"grp": ["A"] * 10, "val": range(10)})
    with pytest.raises(ANOVAError):
        compute_anova(df, factor="grp", response="val")
