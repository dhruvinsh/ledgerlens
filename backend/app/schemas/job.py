from pydantic import BaseModel


class ProcessingJobResponse(BaseModel):
    id: str
    receipt_id: str
    status: str
    stage: str | None
    error_message: str | None
    celery_task_id: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str

    model_config = {"from_attributes": True}
