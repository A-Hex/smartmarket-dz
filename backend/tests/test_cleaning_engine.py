# backend/tests/test_cleaning_engine.py
"""Unit tests for app.services.cleaning.engine (pure functions, synthetic data)."""
import pandas as pd

from app.schemas.cleaning import CleaningConfig, ColumnCleaningConfig
from app.services.cleaning.engine import clean_dataframe


def test_mean_imputation_fills_missing_with_column_mean():
    df = pd.DataFrame({"price": [100.0, 200.0, None, 400.0]})
    config = CleaningConfig(columns=[ColumnCleaningConfig(column="price", missing_strategy="mean")])

    cleaned, report = clean_dataframe(df, config)

    assert cleaned["price"].isna().sum() == 0
    assert abs(cleaned["price"].iloc[2] - (100.0 + 200.0 + 400.0) / 3) < 1e-6
    assert report.per_column[0].null_count_before == 1
    assert report.per_column[0].null_count_after == 0


def test_median_imputation():
    df = pd.DataFrame({"x": [1.0, 2.0, None, 100.0]})
    config = CleaningConfig(columns=[ColumnCleaningConfig(column="x", missing_strategy="median")])
    cleaned, _ = clean_dataframe(df, config)
    assert cleaned["x"].iloc[2] == 2.0  # median of [1, 2, 100]


def test_mode_imputation_categorical():
    df = pd.DataFrame({"region": ["Alger", "Alger", None, "Oran"]})
    config = CleaningConfig(columns=[ColumnCleaningConfig(column="region", missing_strategy="mode")])
    cleaned, _ = clean_dataframe(df, config)
    assert cleaned["region"].iloc[2] == "Alger"


def test_constant_imputation():
    df = pd.DataFrame({"region": ["Alger", None]})
    config = CleaningConfig(
        columns=[ColumnCleaningConfig(column="region", missing_strategy="constant", constant_value="Inconnu")]
    )
    cleaned, _ = clean_dataframe(df, config)
    assert cleaned["region"].iloc[1] == "Inconnu"


def test_drop_rows_removes_rows_with_missing_value():
    df = pd.DataFrame({"x": [1.0, None, 3.0]})
    config = CleaningConfig(columns=[ColumnCleaningConfig(column="x", missing_strategy="drop_rows")])
    cleaned, report = clean_dataframe(df, config)
    assert len(cleaned) == 2
    assert report.rows_before == 3
    assert report.rows_after == 2


def test_drop_column_removes_column_entirely():
    df = pd.DataFrame({"x": [1.0, None], "y": [1, 2]})
    config = CleaningConfig(columns=[ColumnCleaningConfig(column="x", missing_strategy="drop_column")])
    cleaned, report = clean_dataframe(df, config)
    assert "x" not in cleaned.columns
    assert report.columns_after == 1


def test_iqr_outlier_removal_on_known_dataset():
    # Known property: 1000 is a clear IQR outlier among small values 1..10.
    values = list(range(1, 11)) + [1000.0]
    df = pd.DataFrame({"sales": values})
    config = CleaningConfig(
        columns=[ColumnCleaningConfig(column="sales", outlier_method="iqr", outlier_action="remove")]
    )
    cleaned, report = clean_dataframe(df, config)
    assert 1000.0 not in cleaned["sales"].values
    assert report.per_column[0].outliers_detected >= 1
    assert report.per_column[0].outliers_handled == report.per_column[0].outliers_detected


def test_iqr_outlier_capping_bounds_values():
    values = list(range(1, 11)) + [1000.0]
    df = pd.DataFrame({"sales": values})
    config = CleaningConfig(
        columns=[ColumnCleaningConfig(column="sales", outlier_method="iqr", outlier_action="cap")]
    )
    cleaned, report = clean_dataframe(df, config)
    assert cleaned["sales"].max() < 1000.0
    assert len(cleaned) == len(df)  # capping doesn't remove rows


def test_no_strategy_leaves_column_untouched():
    df = pd.DataFrame({"x": [1.0, None, 3.0]})
    config = CleaningConfig(columns=[])
    cleaned, report = clean_dataframe(df, config)
    assert cleaned["x"].isna().sum() == 1
    assert report.per_column == []
