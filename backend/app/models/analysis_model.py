# backend/app/models/analysis_model.py
"""Model — a persisted fitted statistical/ML model (regression, ARIMA, ETS, clustering...)."""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String
from app.db.types import GUID, JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnalysisModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A fitted model, persisted for later validation/forecast/report generation."""

    __tablename__ = "models"

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ols, arima, ets, kmeans, dbscan...
    config: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    fitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
