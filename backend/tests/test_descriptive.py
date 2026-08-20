# backend/tests/test_descriptive.py
"""Unit tests for app.services.analytics.descriptive (pure functions, known-property data)."""
import numpy as np
import pandas as pd
import pytest

from app.services.analytics.descriptive import compute_descriptive_stats


def test_numeric_stats_basic_known_values():
    df = pd.DataFrame({"price": [10.0, 20.0, 30.0, 40.0, 50.0]})
    result = compute_descriptive_stats(df)

    price = result.numeric_columns[0]
    assert price.mean == 30.0
    assert price.median == 30.0
    assert price.min == 10.0
    assert price.max == 50.0
    assert price.count == 5
    assert price.missing == 0
    assert "interpretation" in price.__dataclass_fields__


def test_missing_values_counted_correctly():
    df = pd.DataFrame({"price": [10.0, None, 30.0, None, 50.0]})
    result = compute_descriptive_stats(df)
    price = result.numeric_columns[0]
    assert price.missing == 2
    assert price.count == 3


def test_categorical_frequency_table():
    df = pd.DataFrame({"region": ["Alger", "Alger", "Oran", None]})
    result = compute_descriptive_stats(df)
    region = result.categorical_columns[0]
    assert region.frequency_table == {"Alger": 2, "Oran": 1}
    assert region.missing == 1
    assert region.unique == 2


def test_correlation_matrix_perfect_positive_correlation():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0], "y": [2.0, 4.0, 6.0, 8.0, 10.0]})
    result = compute_descriptive_stats(df)
    assert result.correlation is not None
    idx_x = result.correlation.columns.index("x")
    idx_y = result.correlation.columns.index("y")
    assert result.correlation.pearson[idx_x][idx_y] == pytest.approx(1.0, abs=1e-6)
    assert result.correlation.spearman[idx_x][idx_y] == pytest.approx(1.0, abs=1e-6)


def test_no_correlation_matrix_with_single_numeric_column():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "region": ["A", "B", "C"]})
    result = compute_descriptive_stats(df)
    assert result.correlation is None


def test_target_candidates_excludes_high_missingness_and_constant_columns():
    df = pd.DataFrame(
        {
            "sales": np.arange(100, dtype=float),          # good candidate
            "mostly_missing": [1.0] + [None] * 99,          # excluded: high missingness
            "constant": [5.0] * 100,                        # excluded: zero variance
        }
    )
    result = compute_descriptive_stats(df)
    assert "sales" in result.target_candidates
    assert "mostly_missing" not in result.target_candidates
    assert "constant" not in result.target_candidates


def test_columns_filter_restricts_output():
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0], "c": ["x", "y"]})
    result = compute_descriptive_stats(df, columns=["a", "c"])
    numeric_names = {s.column for s in result.numeric_columns}
    categorical_names = {s.column for s in result.categorical_columns}
    assert numeric_names == {"a"}
    assert categorical_names == {"c"}


def test_skewed_distribution_flagged_in_interpretation():
    # Exponential-like distribution: strong right skew.
    values = [1.0] * 90 + [1000.0] * 10
    df = pd.DataFrame({"x": values})
    result = compute_descriptive_stats(df)
    x = result.numeric_columns[0]
    assert x.skewness is not None
    assert x.skewness > 0.5
    assert "asymétrique" in x.interpretation
