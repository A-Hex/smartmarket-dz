# backend/app/models/dataset.py
"""Dataset and DatasetColumn models."""
import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DatasetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    CLEANING = "cleaning"
    CLEANED = "cleaned"
    ANALYZED = "analyzed"
    FAILED = "failed"


class FileType(str, enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"


class Dataset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An uploaded tabular dataset belonging to a company."""

    __tablename__ = "datasets"

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[FileType] = mapped_column(Enum(FileType, name="file_type"), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status"), default=DatasetStatus.UPLOADED, nullable=False
    )
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    columns: Mapped[List["DatasetColumn"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetColumn(Base, UUIDPrimaryKeyMixin):
    """Column-level profile of a dataset, computed at upload time."""

    __tablename__ = "dataset_columns"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dtype: Mapped[str] = mapped_column(String(50), nullable=False)
    null_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mean_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    std_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_target_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    dataset = relationship("Dataset", back_populates="columns")
