from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.model_config import ModelConfig
    from app.models.receipt import Receipt


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    model_config_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_configs.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    receipt: Mapped[Receipt] = relationship("Receipt", back_populates="processing_jobs")
    model_config: Mapped[ModelConfig | None] = relationship("ModelConfig")
