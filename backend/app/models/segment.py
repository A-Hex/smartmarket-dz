# backend/app/models/segment.py
"""Segment model — output of a customer segmentation (clustering) run."""
import uuid
from typing import Any, Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from app.db.types import GUID, JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Segment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A customer segmentation result (K-Means/DBSCAN + PCA)."""

    __tablename__ = "segments"

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)  # kmeans | dbscan
    n_clusters: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    silhouette: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    centroids: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
