from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User


class Household(BaseMixin, Base):
    __tablename__ = "households"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    sharing_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="shared")

    owner: Mapped[User] = relationship("User", foreign_keys=[owner_id])
    users: Mapped[list[User]] = relationship(
        "User", back_populates="household", foreign_keys="[User.household_id]"
    )
