import uuid
from datetime import datetime

from pydantic import BaseModel


class MonitorListCreate(BaseModel):
    name: str
    list_type: str = "internal"
    external_id: str | None = None
    notes: str | None = None


class MonitorListUpdate(BaseModel):
    name: str | None = None
    list_type: str | None = None
    external_id: str | None = None
    notes: str | None = None


class MonitorListResponse(BaseModel):
    id: uuid.UUID
    name: str
    list_type: str
    external_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MonitorListMembershipCreate(BaseModel):
    target_account_id: uuid.UUID


class MonitorListMembershipResponse(BaseModel):
    id: uuid.UUID
    monitor_list_id: uuid.UUID
    target_account_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
