import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.models import (
    BrowserProfile,
    BrowserProfileStatus,
    LoginSessionStatus,
    MonitoringAccount,
    MonitoringAccountStatus,
)
from app.schemas.common import PaginatedResponse
from app.schemas.login_sessions import LoginSessionCreate, LoginSessionResponse
from app.services import login_sessions as service
from app.services.login_sessions import ConcurrentSessionLimitExceeded
from app.streams import (
    EVT_LOGIN_SESSION_CANCELLED,
    EVT_LOGIN_SESSION_COMPLETED,
    EVT_LOGIN_SESSION_CREATED,
    EVT_LOGIN_SESSION_RUNNING,
    EVT_PROFILE_AVAILABLE,
    EVT_PROFILE_NEEDS_LOGIN,
    WEB_EVENTS,
    StreamClient,
)
from app.streams.messages import WebEventPayload, encode_payload
from app.core.redis import get_redis

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LoginSessionResponse])
async def list_login_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: LoginSessionStatus | None = None,
):
    items, total = await service.get_login_sessions(page=page, page_size=page_size, status=status)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=LoginSessionResponse, status_code=201)
async def create_login_session(data: LoginSessionCreate):
    try:
        session = await service.create_login_session(data)
    except ConcurrentSessionLimitExceeded as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    redis = await get_redis()
    client = StreamClient(redis)

    created_payload = WebEventPayload(
        type=EVT_LOGIN_SESSION_CREATED,
        payload={"session_id": str(session.id), "status": "pending"},
    )
    await client.xadd(WEB_EVENTS, encode_payload(created_payload))

    running_payload = WebEventPayload(
        type=EVT_LOGIN_SESSION_RUNNING,
        payload={"session_id": str(session.id), "status": "running"},
    )
    await client.xadd(WEB_EVENTS, encode_payload(running_payload))

    return session


@router.get("/novnc-auth")
async def novnc_auth(request: Request, token: str = Query(...)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    valid = await service.validate_novnc_token(token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    return None


@router.get("/{session_id}", response_model=LoginSessionResponse)
async def get_login_session(session_id: uuid.UUID):
    session = await service.get_login_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Login session not found")
    return session


@router.post("/{session_id}/complete", response_model=LoginSessionResponse)
async def complete_login_session(session_id: uuid.UUID):
    session = await service.update_login_session_status(session_id, LoginSessionStatus.COMPLETED)
    if session is None:
        raise HTTPException(status_code=404, detail="Login session not found")

    async with async_session_factory() as db:
        if session.browser_profile_id:
            await db.execute(
                update(BrowserProfile)
                .where(BrowserProfile.id == session.browser_profile_id)
                .values(status=BrowserProfileStatus.AVAILABLE)
            )
        if session.monitoring_account_id:
            await db.execute(
                update(MonitoringAccount)
                .where(MonitoringAccount.id == session.monitoring_account_id)
                .values(status=MonitoringAccountStatus.ACTIVE, last_login_check_at=datetime.now(timezone.utc))
            )
        await db.commit()

    redis = await get_redis()
    client = StreamClient(redis)
    payload = WebEventPayload(
        type=EVT_LOGIN_SESSION_COMPLETED,
        payload={
            "session_id": str(session_id),
            "status": "completed",
            "browser_profile_id": str(session.browser_profile_id) if session.browser_profile_id else None,
            "monitoring_account_id": str(session.monitoring_account_id) if session.monitoring_account_id else None,
        },
    )
    await client.xadd(WEB_EVENTS, encode_payload(payload))

    if session.browser_profile_id:
        profile_payload = WebEventPayload(
            type=EVT_PROFILE_AVAILABLE,
            payload={"profile_id": str(session.browser_profile_id), "status": "available"},
        )
        await client.xadd(WEB_EVENTS, encode_payload(profile_payload))

    return session


@router.post("/{session_id}/cancel", response_model=LoginSessionResponse)
async def cancel_login_session(session_id: uuid.UUID):
    session = await service.update_login_session_status(session_id, LoginSessionStatus.CANCELLED)
    if session is None:
        raise HTTPException(status_code=404, detail="Login session not found")

    async with async_session_factory() as db:
        if session.browser_profile_id:
            await db.execute(
                update(BrowserProfile)
                .where(BrowserProfile.id == session.browser_profile_id)
                .values(status=BrowserProfileStatus.NEEDS_LOGIN)
            )
        if session.monitoring_account_id:
            await db.execute(
                update(MonitoringAccount)
                .where(MonitoringAccount.id == session.monitoring_account_id)
                .values(status=MonitoringAccountStatus.NEEDS_LOGIN)
            )
        await db.commit()

    redis = await get_redis()
    client = StreamClient(redis)
    payload = WebEventPayload(
        type=EVT_LOGIN_SESSION_CANCELLED,
        payload={"session_id": str(session_id), "status": "cancelled"},
    )
    await client.xadd(WEB_EVENTS, encode_payload(payload))

    if session.browser_profile_id:
        profile_payload = WebEventPayload(
            type=EVT_PROFILE_NEEDS_LOGIN,
            payload={"profile_id": str(session.browser_profile_id), "status": "needs_login"},
        )
        await client.xadd(WEB_EVENTS, encode_payload(profile_payload))

    return session
