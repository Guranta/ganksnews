import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import BrowserProfileStatus


class BrowserProfileCreate(BaseModel):
    name: str
    profile_path: str
    monitoring_account_id: uuid.UUID | None = None
    provider: str = "cloakbrowser"


class BrowserProfileUpdate(BaseModel):
    name: str | None = None
    profile_path: str | None = None
    monitoring_account_id: uuid.UUID | None = None
    status: BrowserProfileStatus | None = None
    provider: str | None = None


class BrowserProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    profile_path: str
    monitoring_account_id: uuid.UUID | None
    status: BrowserProfileStatus
    provider: str
    last_health_check_at: datetime | None
    locked_by: str | None
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
