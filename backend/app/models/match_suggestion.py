from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.canonical_item import CanonicalItem
    from app.models.line_item import LineItem


class MatchSuggestion(Base):
    __tablename__ = "match_suggestions"
    __table_args__ = (
        UniqueConstraint("line_item_id", "canonical_item_id", name="uq_suggestion_pair"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    line_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("line_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("canonical_items.id", ondelete="CASCADE"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    line_item: Mapped[LineItem] = relationship("LineItem", back_populates="match_suggestions")
    canonical_item: Mapped[CanonicalItem] = relationship("CanonicalItem")
