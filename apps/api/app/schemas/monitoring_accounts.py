import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import MonitoringAccountStatus


class MonitoringAccountCreate(BaseModel):
    username: str
    display_name: str | None = None
    notes: str | None = None


class MonitoringAccountUpdate(BaseModel):
    display_name: str | None = None
    status: MonitoringAccountStatus | None = None
    notes: str | None = None


class MonitoringAccountResponse(BaseModel):
    id: uuid.UUID
    platform: str
    username: str
    display_name: str | None
    status: MonitoringAccountStatus
    notes: str | None
    last_login_check_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
