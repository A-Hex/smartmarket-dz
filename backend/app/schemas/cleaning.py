# backend/app/schemas/cleaning.py
"""Pydantic v2 schemas for the Data Cleaning Engine."""
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MissingStrategy = Literal["mean", "median", "mode", "constant", "drop_rows", "drop_column", "none"]
OutlierMethod = Literal["iqr", "zscore", "none"]
OutlierAction = Literal["remove", "cap", "none"]


class ColumnCleaningConfig(BaseModel):
    """Per-column cleaning strategy, as configured from the Data Cleaning UI."""

    column: str
    missing_strategy: MissingStrategy = "none"
    constant_value: Optional[Any] = None  # used when missing_strategy == "constant"
    outlier_method: OutlierMethod = "none"
    outlier_action: OutlierAction = "none"


class CleaningConfig(BaseModel):
    """Full cleaning job configuration: a strategy per column that needs one."""

    columns: list[ColumnCleaningConfig] = Field(default_factory=list)


class ColumnCleaningReport(BaseModel):
    column: str
    null_count_before: int
    null_count_after: int
    outliers_detected: int
    outliers_handled: int
    strategy_applied: str


class CleaningReport(BaseModel):
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    per_column: list[ColumnCleaningReport]
    cleaned_storage_path: str


class CleaningRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    config: dict
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    report: Optional[dict] = None
    created_at: datetime
