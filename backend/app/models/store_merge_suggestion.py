from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.user import User


class StoreMergeSuggestion(Base):
    __tablename__ = "store_merge_suggestions"
    __table_args__ = (
        UniqueConstraint("store_a_id", "store_b_id", name="uq_store_merge_pair"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    store_a_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_b_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    store_a: Mapped[Store] = relationship("Store", foreign_keys=[store_a_id])
    store_b: Mapped[Store] = relationship("Store", foreign_keys=[store_b_id])
    resolver: Mapped[User | None] = relationship("User", foreign_keys=[resolved_by])
