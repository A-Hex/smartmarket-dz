# backend/tests/test_profiling.py
"""Unit tests for app.services.datasets.profiling (pure functions, no DB/HTTP)."""
import numpy as np
import pandas as pd
import pytest

from app.services.datasets.profiling import preview_rows, profile_dataframe


def test_profile_dataframe_basic_stats():
    df = pd.DataFrame(
        {
            "price": [100.0, 200.0, None, 400.0, 500.0],
            "region": ["Alger", "Oran", "Alger", "Constantine", "Oran"],
        }
    )
    profile = profile_dataframe(df)

    assert profile.row_count == 5
    assert profile.column_count == 2

    price_col = next(c for c in profile.columns if c.name == "price")
    assert price_col.null_count == 1
    assert price_col.min_value == 100.0
    assert price_col.max_value == 500.0
    assert price_col.mean_value == pytest.approx(300.0)

    region_col = next(c for c in profile.columns if c.name == "region")
    assert region_col.unique_count == 3
    assert region_col.is_target_candidate is False  # non-numeric


def test_target_candidate_flagging():
    # Low missingness, decent variance/uniqueness -> candidate
    df = pd.DataFrame({"sales": np.arange(100, dtype=float)})
    profile = profile_dataframe(df)
    sales_col = profile.columns[0]
    assert sales_col.is_target_candidate is True


def test_near_constant_numeric_column_not_a_candidate():
    df = pd.DataFrame({"flag": [1] * 100})
    profile = profile_dataframe(df)
    flag_col = profile.columns[0]
    assert flag_col.is_target_candidate is False


def test_preview_rows_converts_nan_to_none():
    df = pd.DataFrame({"a": [1, None, 3]})
    rows = preview_rows(df, limit=10)
    assert rows[1]["a"] is None
    assert len(rows) == 3
