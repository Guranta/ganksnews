import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import TargetAccountPriority, TargetAccountStatus


class TargetAccountCreate(BaseModel):
    username: str
    display_name: str | None = None
    bio: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    priority: TargetAccountPriority = TargetAccountPriority.NORMAL


class TargetAccountUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    status: TargetAccountStatus | None = None
    priority: TargetAccountPriority | None = None


class TargetAccountResponse(BaseModel):
    id: uuid.UUID
    platform: str
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    tags: list[str] | None
    notes: str | None
    status: TargetAccountStatus
    priority: TargetAccountPriority
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TargetAccountBulkImportRequest(BaseModel):
    text: str


class TargetAccountBulkImportResponse(BaseModel):
    batch_id: uuid.UUID
    total_count: int
    created_count: int
    updated_count: int
    failed_count: int
    errors: list[str] | None = None

    model_config = {"from_attributes": True}
