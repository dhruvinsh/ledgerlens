import asyncio
import logging

from celery.exceptions import SoftTimeLimitExceeded

from app.worker import celery_app

from app.services.notifications import publish_job_update

logger = logging.getLogger(__name__)

# Worker-local async engine and session factory, set on worker_process_init
_engine = None
_session_factory = None


def _get_session_factory():  # type: ignore[no-untyped-def]
    global _engine, _session_factory
    if _session_factory is None:
        from sqlalchemy import event
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy.pool import NullPool

        from app.core.config import settings

        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            poolclass=NullPool,
        )
        _session_factory = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )

        if "sqlite" in settings.DATABASE_URL:

            @event.listens_for(_engine.sync_engine, "connect")
            def _set_pragmas(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

    return _session_factory


def _notify(
    user_id: str, job_id: str, status: str, receipt_id: str,
    stage: str | None = None, error_message: str | None = None,
) -> None:
    publish_job_update(user_id, job_id, status, receipt_id, stage=stage, error_message=error_message)


@celery_app.task(bind=True, name="process_receipt")
def process_receipt_task(self, job_id: str) -> dict:  # type: ignore[no-untyped-def]
    """Process a receipt: OCR → LLM/heuristic → normalize → persist."""
    return asyncio.run(_process(self, job_id))


async def _process(task, job_id: str) -> dict:  # type: ignore[no-untyped-def]
    from app.core.time import utc_now
    from app.models.processing_job import ProcessingJob
    from app.models.receipt import Receipt
    from app.services.extraction import run_extraction

    session_factory = _get_session_factory()
    async with session_factory() as db:
        # Load job
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        result = await db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            logger.error("ProcessingJob %s not found", job_id)
            return {"status": "error", "message": "Job not found"}

        # Load receipt
        result = await db.execute(
            select(Receipt).where(Receipt.id == job.receipt_id)
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            logger.error("Receipt %s not found for job %s", job.receipt_id, job_id)
            job.status = "failed"
            job.error_message = "Receipt not found"
            await db.commit()
            return {"status": "error", "message": "Receipt not found"}

        # Mark running
        job.status = "running"
        job.started_at = utc_now()
        job.celery_task_id = task.request.id
        receipt.status = "processing"
        await db.commit()

        _notify(receipt.user_id, job.id, "running", receipt.id, stage="ocr")

        try:
            # Resolve model config if set
            model_kwargs: dict = {}
            if job.model_config_id:
                from app.models.model_config import ModelConfig

                mc_result = await db.execute(
                    select(ModelConfig).where(ModelConfig.id == job.model_config_id)
                )
                mc = mc_result.scalar_one_or_none()
                if mc:
                    model_kwargs = {
                        "model_base_url": mc.base_url,
                        "model_name": mc.model_name,
                        "model_api_key": mc.api_key_encrypted,
                        "model_timeout": mc.timeout_seconds,
                        "model_max_retries": mc.max_retries,
                        "supports_vision": mc.supports_vision,
                    }

            # OCR stage
            job.stage = "ocr"
            await db.commit()

            # Extraction stage (includes OCR internally)
            job.stage = "extraction"
            await db.commit()

            await run_extraction(receipt, db, **model_kwargs)

            # Done
            job.status = "completed"
            job.stage = "done"
            job.completed_at = utc_now()

            # Surface LLM failure as a warning on the job
            if (
                receipt.extraction_source == "heuristic"
                and model_kwargs  # A model config was set but LLM still failed
            ):
                job.error_message = (
                    "LLM/vision extraction failed — used heuristic fallback. "
                    "Check that the configured model is running and accessible."
                )

            await db.commit()

            _notify(
                receipt.user_id, job.id, "completed", receipt.id,
                stage="done", error_message=job.error_message,
            )

            logger.info(
                "Receipt %s processed (source=%s)", receipt.id, receipt.extraction_source
            )
            return {"status": "completed", "receipt_id": receipt.id}

        except SoftTimeLimitExceeded:
            job.status = "failed"
            job.error_message = "Processing timed out"
            job.completed_at = utc_now()
            receipt.status = "failed"
            await db.commit()
            _notify(receipt.user_id, job.id, "failed", receipt.id, error_message=job.error_message)
            raise

        except Exception as e:
            logger.exception("Processing failed for receipt %s", receipt.id)
            job.status = "failed"
            job.error_message = str(e)[:1000]
            job.completed_at = utc_now()
            receipt.status = "failed"
            await db.commit()
            _notify(receipt.user_id, job.id, "failed", receipt.id, error_message=job.error_message)
            return {"status": "failed", "error": str(e)}
