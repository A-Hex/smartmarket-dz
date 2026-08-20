# backend/app/models/kpi.py
"""KPI model — a single computed KPI value with its formula and timestamp."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class KPIType(str, enum.Enum):
    CLTV = "cltv"
    CHURN = "churn"
    TAKE_RATE = "take_rate"
    CAC = "cac"
    WOM = "wom"
    REVENUE_GROWTH = "revenue_growth"
    GROSS_MARGIN = "gross_margin"


class KPI(Base, UUIDPrimaryKeyMixin):
    """A computed KPI value for a company/dataset at a point in time."""

    __tablename__ = "kpis"

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kpi_type: Mapped[KPIType] = mapped_column(Enum(KPIType, name="kpi_type"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    formula: Mapped[str] = mapped_column(String(500), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
