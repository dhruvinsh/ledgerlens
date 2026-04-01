import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ActiveJobExistsError
from app.core.time import utc_now
from app.models.processing_job import ProcessingJob
from app.repositories.model_config import ModelConfigRepository
from app.repositories.processing_job import ProcessingJobRepository


async def enqueue_receipt(receipt_id: str, db: AsyncSession) -> ProcessingJob:
    """Create a ProcessingJob and dispatch the Celery task."""
    repo = ProcessingJobRepository(db)

    # Check for existing active job
    active = await repo.get_active_for_receipt(receipt_id)
    if active:
        raise ActiveJobExistsError(
            f"Receipt {receipt_id} already has an active processing job"
        )

    # Attach the default active model config so the worker uses it
    mc_repo = ModelConfigRepository(db)
    default_model = await mc_repo.get_default_active()

    job = ProcessingJob(
        id=str(uuid.uuid4()),
        receipt_id=receipt_id,
        status="queued",
        model_config_id=default_model.id if default_model else None,
        created_at=utc_now(),
    )
    await repo.create(job)
    await db.commit()

    # Import here to avoid circular imports at module level
    from app.tasks.receipt_processing import process_receipt_task

    celery_result = process_receipt_task.delay(job.id)
    job.celery_task_id = celery_result.id
    await db.commit()

    return job
