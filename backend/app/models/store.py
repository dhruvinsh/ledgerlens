from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.receipt import Receipt


class Store(BaseMixin, Base):
    __tablename__ = "stores"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    receipts: Mapped[list[Receipt]] = relationship("Receipt", back_populates="store")
