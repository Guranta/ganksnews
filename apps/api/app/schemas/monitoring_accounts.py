from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import BrowserProfileStatus, MonitoringAccountStatus
from app.schemas.browser_profiles import BrowserProfileResponse
from app.schemas.login_sessions import LoginSessionResponse


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


class MonitoringAccountWithLoginSessionCreate(BaseModel):
    username: str
    display_name: str | None = None
    notes: str | None = None


class MonitoringAccountWithLoginSessionResponse(BaseModel):
    account: MonitoringAccountResponse
    browser_profile: BrowserProfileResponse
    login_session: LoginSessionResponse
    vnc_url: str | None


class CookieImportRequest(BaseModel):
    cookies: list[dict]
    source: str | None = None
    notes: str | None = None


class LoginHealthResponse(BaseModel):
    status: MonitoringAccountStatus
    profile_status: BrowserProfileStatus
    reason: str
    checked_at: datetime
    final_url: str | None = None
    http_status: int | None = None
    duration_ms: int | None = None


class CookieImportResponse(BaseModel):
    account: MonitoringAccountResponse
    browser_profile: BrowserProfileResponse
    health_check: LoginHealthResponse


class MonitoringAccountHealthCheckResponse(BaseModel):
    account: MonitoringAccountResponse
    browser_profile: BrowserProfileResponse
    health_check: LoginHealthResponse
