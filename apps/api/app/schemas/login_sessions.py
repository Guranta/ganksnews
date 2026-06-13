from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class LoginSessionCreate(BaseModel):
    browser_profile_id: uuid.UUID | None = None
    monitoring_account_id: uuid.UUID | None = None


class LoginSessionUpdate(BaseModel):
    status: str | None = None
    vnc_url: str | None = None
    error_message: str | None = None


class LoginSessionResponse(BaseModel):
    id: uuid.UUID
    browser_profile_id: uuid.UUID | None
    monitoring_account_id: uuid.UUID | None
    status: str
    vnc_url: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
