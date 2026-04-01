from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import JobNotFoundError
from app.models.processing_job import ProcessingJob
from app.models.receipt import Receipt
from app.models.user import User
from app.repositories.processing_job import ProcessingJobRepository
from app.schemas.job import ProcessingJobResponse
from app.schemas.pagination import PaginatedResponse
from app.services.scope import receipt_visibility

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_response(job: ProcessingJob) -> ProcessingJobResponse:
    return ProcessingJobResponse(
        id=job.id,
        receipt_id=job.receipt_id,
        status=job.status,
        stage=job.stage,
        error_message=job.error_message,
        celery_task_id=job.celery_task_id,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        created_at=job.created_at.isoformat(),
    )


@router.get("", response_model=PaginatedResponse[ProcessingJobResponse])
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProcessingJobResponse]:
    from sqlalchemy import func

    vis = receipt_visibility(user)
    base = (
        select(ProcessingJob)
        .join(Receipt, ProcessingJob.receipt_id == Receipt.id)
        .where(vis)
    )

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = base.order_by(ProcessingJob.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    jobs = list(result.scalars().all())

    return PaginatedResponse(
        items=[_to_response(j) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProcessingJobResponse:
    repo = ProcessingJobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job:
        raise JobNotFoundError(f"Job {job_id} not found")
    return _to_response(job)
