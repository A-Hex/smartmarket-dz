# backend/app/models/forecast.py
"""Forecast model — output of a demand forecasting run (ARIMA/ETS)."""
import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer
from app.db.types import GUID, JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Forecast(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Point forecast + confidence intervals + holdout metrics for a fitted model."""

    __tablename__ = "forecasts"

    model_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    point: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    ci_lower: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    ci_upper: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)  # MAE/RMSE/MAPE
