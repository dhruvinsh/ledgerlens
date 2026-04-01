from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.receipt import Receipt


class User(BaseMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    household_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("households.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    household: Mapped[Household | None] = relationship(
        "Household", back_populates="users", foreign_keys=[household_id]
    )
    receipts: Mapped[list[Receipt]] = relationship("Receipt", back_populates="user")
