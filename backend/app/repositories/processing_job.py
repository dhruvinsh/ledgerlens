from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.processing_job import ProcessingJob


class ProcessingJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: str) -> ProcessingJob | None:
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_receipt(self, receipt_id: str) -> ProcessingJob | None:
        result = await self.db.execute(
            select(ProcessingJob).where(
                ProcessingJob.receipt_id == receipt_id,
                ProcessingJob.status.in_(["queued", "running"]),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, job: ProcessingJob) -> ProcessingJob:
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_orphaned_running(self, max_age_seconds: int) -> list[ProcessingJob]:
        from datetime import timedelta

        cutoff = utc_now() - timedelta(seconds=max_age_seconds)
        result = await self.db.execute(
            select(ProcessingJob).where(
                ProcessingJob.status == "running",
                ProcessingJob.started_at < cutoff,
            )
        )
        return list(result.scalars().all())

    async def get_orphaned_queued(self, max_age_seconds: int = 60) -> list[ProcessingJob]:
        from datetime import timedelta

        cutoff = utc_now() - timedelta(seconds=max_age_seconds)
        result = await self.db.execute(
            select(ProcessingJob).where(
                ProcessingJob.status == "queued",
                ProcessingJob.created_at < cutoff,
            )
        )
        return list(result.scalars().all())
