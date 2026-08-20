# backend/app/schemas/dataset.py
"""Pydantic v2 schemas for Dataset / DatasetColumn resources."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.dataset import DatasetStatus, FileType


class DatasetColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    dtype: str
    null_count: int
    unique_count: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    is_target_candidate: bool


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    original_filename: str
    file_type: FileType
    status: DatasetStatus
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    created_at: datetime


class DatasetDetailRead(DatasetRead):
    columns: list[DatasetColumnRead] = []


class DatasetPreviewRead(BaseModel):
    columns: list[str]
    rows: list[dict]
    total_rows: int
    preview_rows: int
