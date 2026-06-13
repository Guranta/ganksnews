import uuid
from datetime import datetime

from pydantic import BaseModel


class WorkerResponse(BaseModel):
    id: uuid.UUID
    worker_type: str
    worker_id: str
    status: str
    current_task: str | None
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkerSummary(BaseModel):
    worker_type: str
    running: int
    stopped: int
    error: int
    total: int
    workers: list[WorkerResponse]
