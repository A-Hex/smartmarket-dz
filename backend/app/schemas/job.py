# backend/app/schemas/job.py
"""Pydantic v2 schema for the AnalysisJob resource."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.analysis_job import JobStatus, JobType


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    dataset_id: UUID
    type: JobType
    config: dict[str, Any]
    status: JobStatus
    progress: float
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
