from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.store import Store


class StoreAlias(BaseMixin, Base):
    __tablename__ = "store_aliases"
    __table_args__ = (
        UniqueConstraint("alias_name_lower", name="uq_store_alias_name"),
    )

    store_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_name_lower: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ocr")

    store: Mapped[Store] = relationship("Store", back_populates="aliases")
