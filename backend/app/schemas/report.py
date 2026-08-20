# backend/app/schemas/report.py
"""Pydantic v2 schemas for report generation."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportFormat, ReportType


class ReportGenerateRequest(BaseModel):
    """Config for POST /reports/generate."""

    dataset_id: UUID
    format: ReportFormat
    type: ReportType = Field(
        default=ReportType.EXECUTIVE,
        description="'executive' -> PDF summary; 'raw_results' -> full XLSX workbook. "
        "Each format has one natural type, but both are accepted for any format.",
    )


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    type: ReportType
    format: ReportFormat
    storage_path: str
    created_at: datetime
