# backend/app/models/decision.py
"""Decision model — a prioritized, evidence-backed recommendation from the Decision Engine."""
import enum
import uuid
from typing import Any

from sqlalchemy import Enum, ForeignKey, String, Text
from app.db.types import GUID, JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DecisionPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    APPLIED = "applied"
    DISMISSED = "dismissed"


class Decision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single recommendation emitted by the rule-based Decision Engine."""

    __tablename__ = "decisions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    priority: Mapped[DecisionPriority] = mapped_column(
        Enum(DecisionPriority, name="decision_priority"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DecisionStatus] = mapped_column(
        Enum(DecisionStatus, name="decision_status"), default=DecisionStatus.OPEN, nullable=False
    )
