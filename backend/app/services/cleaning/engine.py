# backend/app/services/cleaning/engine.py
"""
Data Cleaning Engine.

Pure function of (DataFrame, CleaningConfig) -> (cleaned DataFrame, CleaningReport).
No DB/HTTP concerns, so it is independently unit-testable and safe to later wrap
in a Celery task without touching the logic itself.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.schemas.cleaning import CleaningConfig, ColumnCleaningConfig


@dataclass
class ColumnCleaningResult:
    column: str
    null_count_before: int
    null_count_after: int
    outliers_detected: int
    outliers_handled: int
    strategy_applied: str


@dataclass
class CleaningResult:
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    per_column: list[ColumnCleaningResult] = field(default_factory=list)


def _iqr_bounds(series: pd.Series) -> tuple[float, float]:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def _zscore_bounds(series: pd.Series, threshold: float = 3.0) -> tuple[float, float]:
    mean, std = series.mean(), series.std()
    if std == 0 or np.isnan(std):
        return series.min(), series.max()
    return mean - threshold * std, mean + threshold * std


def _detect_outlier_mask(series: pd.Series, method: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if method == "iqr":
        lower, upper = _iqr_bounds(numeric)
    elif method == "zscore":
        lower, upper = _zscore_bounds(numeric)
    else:
        return pd.Series(False, index=series.index)
    return (numeric < lower) | (numeric > upper)


def _apply_missing_strategy(
    df: pd.DataFrame, col_cfg: ColumnCleaningConfig
) -> tuple[pd.DataFrame, str]:
    col = col_cfg.column
    strategy = col_cfg.missing_strategy
    if col not in df.columns or strategy == "none":
        return df, "none"

    series = df[col]
    is_numeric = pd.api.types.is_numeric_dtype(series)

    if strategy == "mean" and is_numeric:
        df[col] = series.fillna(series.mean())
    elif strategy == "median" and is_numeric:
        df[col] = series.fillna(series.median())
    elif strategy == "mode":
        mode = series.mode(dropna=True)
        if not mode.empty:
            df[col] = series.fillna(mode.iloc[0])
    elif strategy == "constant":
        df[col] = series.fillna(col_cfg.constant_value)
    elif strategy == "drop_rows":
        df = df.dropna(subset=[col])
    elif strategy == "drop_column":
        df = df.drop(columns=[col])

    return df, strategy


def _apply_outlier_handling(
    df: pd.DataFrame, col_cfg: ColumnCleaningConfig
) -> tuple[pd.DataFrame, int, int]:
    col = col_cfg.column
    if col not in df.columns or col_cfg.outlier_method == "none" or col_cfg.outlier_action == "none":
        return df, 0, 0
    if not pd.api.types.is_numeric_dtype(df[col]):
        return df, 0, 0

    mask = _detect_outlier_mask(df[col], col_cfg.outlier_method)
    detected = int(mask.sum())
    handled = 0

    if detected == 0:
        return df, 0, 0

    if col_cfg.outlier_action == "remove":
        df = df.loc[~mask]
        handled = detected
    elif col_cfg.outlier_action == "cap":
        numeric = pd.to_numeric(df[col], errors="coerce")
        if col_cfg.outlier_method == "iqr":
            lower, upper = _iqr_bounds(numeric)
        else:
            lower, upper = _zscore_bounds(numeric)
        df[col] = numeric.clip(lower=lower, upper=upper)
        handled = detected

    return df, detected, handled


def clean_dataframe(df: pd.DataFrame, config: CleaningConfig) -> tuple[pd.DataFrame, CleaningResult]:
    """
    Apply the configured per-column missing-value and outlier strategies.

    Order per column: handle missing values first, then outliers (so imputed
    values are also eligible for outlier detection/handling).
    """
    df = df.copy()
    rows_before, columns_before = len(df), len(df.columns)
    per_column: list[ColumnCleaningResult] = []

    for col_cfg in config.columns:
        col = col_cfg.column
        if col not in df.columns:
            continue

        null_before = int(df[col].isna().sum())

        df, missing_strategy_applied = _apply_missing_strategy(df, col_cfg)

        if col not in df.columns:  # dropped entirely
            per_column.append(
                ColumnCleaningResult(
                    column=col,
                    null_count_before=null_before,
                    null_count_after=0,
                    outliers_detected=0,
                    outliers_handled=0,
                    strategy_applied=missing_strategy_applied,
                )
            )
            continue

        null_after_missing = int(df[col].isna().sum())

        df, detected, handled = _apply_outlier_handling(df, col_cfg)

        null_after = int(df[col].isna().sum()) if col in df.columns else null_after_missing

        strategy_label = missing_strategy_applied
        if col_cfg.outlier_method != "none" and col_cfg.outlier_action != "none":
            strategy_label = f"{missing_strategy_applied}+outlier:{col_cfg.outlier_method}:{col_cfg.outlier_action}"

        per_column.append(
            ColumnCleaningResult(
                column=col,
                null_count_before=null_before,
                null_count_after=null_after,
                outliers_detected=detected,
                outliers_handled=handled,
                strategy_applied=strategy_label,
            )
        )

    df = df.reset_index(drop=True)
    result = CleaningResult(
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=columns_before,
        columns_after=len(df.columns),
        per_column=per_column,
    )
    return df, result
