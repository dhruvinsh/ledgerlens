from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.line_item import LineItem
    from app.models.processing_job import ProcessingJob
    from app.models.store import Store
    from app.models.user import User


class Receipt(BaseMixin, Base):
    __tablename__ = "receipts"
    __table_args__ = (
        Index("ix_receipts_user_date", "user_id", "transaction_date"),
        Index("ix_receipts_household_date", "household_id", "transaction_date"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    household_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("households.id", ondelete="SET NULL"), nullable=True
    )
    store_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CAD")
    subtotal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tax: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_of: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="receipts")
    household: Mapped[None] = relationship("Household")
    store: Mapped[Store | None] = relationship("Store", back_populates="receipts")
    line_items: Mapped[list[LineItem]] = relationship(
        "LineItem", back_populates="receipt", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list[ProcessingJob]] = relationship(
        "ProcessingJob", back_populates="receipt", cascade="all, delete-orphan"
    )
    duplicate_parent: Mapped[Receipt | None] = relationship(
        "Receipt", remote_side="Receipt.id", foreign_keys=[duplicate_of]
    )
