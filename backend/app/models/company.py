# backend/app/models/company.py
"""Company model — the multi-tenancy root entity."""
from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tenant company. Every business table is scoped by company_id."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="DZ", nullable=False)

    users: Mapped[List["User"]] = relationship(back_populates="company", cascade="all, delete-orphan")
