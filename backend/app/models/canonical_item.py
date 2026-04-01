from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BaseMixin


class CanonicalItem(BaseMixin, Base):
    __tablename__ = "canonical_items"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    image_fetch_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
