# backend/app/models/report.py
"""Report model — a generated PDF/XLSX export."""
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReportType(str, enum.Enum):
    EXECUTIVE = "executive"
    RAW_RESULTS = "raw_results"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    XLSX = "xlsx"


class Report(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A generated, downloadable report file."""

    __tablename__ = "reports"

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ReportType] = mapped_column(Enum(ReportType, name="report_type"), nullable=False)
    format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat, name="report_format"), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
