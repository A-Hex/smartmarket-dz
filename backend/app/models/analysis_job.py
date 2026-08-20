# backend/app/models/analysis_job.py
"""AnalysisJob model — tracks async Celery analytics job status/progress/result."""
import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text
from app.db.types import GUID, JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobType(str, enum.Enum):
    DESCRIPTIVE = "descriptive"
    REGRESSION = "regression"
    ANOVA = "anova"
    VALIDATION = "validation"
    FORECAST = "forecast"
    SEGMENTATION = "segmentation"
    KPI = "kpi"
    DECISION = "decision"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A queued/running/completed analytics job with immutable result history."""

    __tablename__ = "analysis_jobs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.QUEUED, nullable=False
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
