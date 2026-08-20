# backend/app/models/cleaning_run.py
"""CleaningRun model — records a data cleaning job execution and its report."""
import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey
from app.db.types import GUID, JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CleaningStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CleaningRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One execution of the Data Cleaning Engine against a dataset."""

    __tablename__ = "cleaning_runs"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    status: Mapped[CleaningStatus] = mapped_column(
        Enum(CleaningStatus, name="cleaning_status"), default=CleaningStatus.QUEUED, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    report: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
