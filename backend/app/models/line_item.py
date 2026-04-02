from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.canonical_item import CanonicalItem
    from app.models.match_suggestion import MatchSuggestion
    from app.models.receipt import Receipt


class LineItem(Base):
    __tablename__ = "line_items"
    __table_args__ = (
        Index("ix_line_items_receipt_position", "receipt_id", "position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    canonical_item_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("canonical_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_refund: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tax_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    weight_qty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    receipt: Mapped[Receipt] = relationship("Receipt", back_populates="line_items")
    canonical_item: Mapped[CanonicalItem | None] = relationship("CanonicalItem")
    match_suggestions: Mapped[list[MatchSuggestion]] = relationship(
        "MatchSuggestion", back_populates="line_item", cascade="all, delete-orphan"
    )
