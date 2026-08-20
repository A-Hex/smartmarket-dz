# backend/app/services/datasets/profiling.py
"""
Column profiling: reads an uploaded CSV/XLSX and produces per-column statistics.

Pure function of (file path, file type) -> profile. No DB or HTTP concerns here,
so it is independently unit-testable, per the architecture requirement that
analytics/ingestion services are pure functions of (dataset, config) -> result.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from app.schemas.errors import ApiError

MAX_PREVIEW_ROWS_DEFAULT = 100
# A numeric column is a "target candidate" if it has low missingness and
# reasonable variance (not a near-constant / id-like column).
TARGET_CANDIDATE_MAX_NULL_RATIO = 0.10
TARGET_CANDIDATE_MIN_UNIQUE_RATIO = 0.05


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_count: int
    unique_count: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    is_target_candidate: bool = False


@dataclass
class DatasetProfile:
    row_count: int
    column_count: int
    columns: list[ColumnProfile] = field(default_factory=list)


def read_dataset_file(storage_path: str, file_type: str) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame, with clear errors on failure."""
    try:
        if file_type == "csv":
            # Try utf-8 first, then fall back to latin-1 for common Algerian/French exports.
            try:
                return pd.read_csv(storage_path, encoding="utf-8")
            except UnicodeDecodeError:
                return pd.read_csv(storage_path, encoding="latin-1")
        elif file_type in ("xlsx", "xls"):
            return pd.read_excel(storage_path)
        else:
            raise ApiError(422, "unsupported_file_type", "Type de fichier non supporté.")
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            422,
            "file_parse_error",
            f"Impossible de lire le fichier : {exc}",
        ) from exc


def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    """Compute per-column statistics and flag numeric target-variable candidates."""
    n_rows = len(df)
    columns: list[ColumnProfile] = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))
        is_numeric = pd.api.types.is_numeric_dtype(series)

        min_v = max_v = mean_v = std_v = None
        if is_numeric and n_rows > 0:
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                min_v = float(np.nanmin(numeric))
                max_v = float(np.nanmax(numeric))
                mean_v = float(np.nanmean(numeric))
                std_v = float(np.nanstd(numeric)) if numeric.notna().sum() > 1 else 0.0

        is_candidate = False
        if is_numeric and n_rows > 0:
            null_ratio = null_count / n_rows
            unique_ratio = unique_count / n_rows
            is_candidate = (
                null_ratio <= TARGET_CANDIDATE_MAX_NULL_RATIO
                and unique_ratio >= TARGET_CANDIDATE_MIN_UNIQUE_RATIO
            )

        columns.append(
            ColumnProfile(
                name=str(col),
                dtype=str(series.dtype),
                null_count=null_count,
                unique_count=unique_count,
                min_value=min_v,
                max_value=max_v,
                mean_value=mean_v,
                std_value=std_v,
                is_target_candidate=is_candidate,
            )
        )

    return DatasetProfile(row_count=n_rows, column_count=len(df.columns), columns=columns)


def preview_rows(df: pd.DataFrame, limit: int = MAX_PREVIEW_ROWS_DEFAULT) -> list[dict]:
    """Return the first `limit` rows as JSON-safe records (NaN -> None)."""
    head = df.head(limit)
    # Replace NaN/NaT with None so the payload is valid JSON.
    return head.astype(object).where(pd.notna(head), None).to_dict(orient="records")
