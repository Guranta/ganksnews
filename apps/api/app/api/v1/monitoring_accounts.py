import uuid

from fastapi import APIRouter, HTTPException, Query

from app.browser.cookies import CookieImportError
from app.core.redis import get_redis
from app.schemas.common import PaginatedResponse
from app.schemas.monitoring_accounts import (
    CookieImportRequest,
    CookieImportResponse,
    LoginHealthResponse,
    MonitoringAccountCreate,
    MonitoringAccountHealthCheckResponse,
    MonitoringAccountResponse,
    MonitoringAccountUpdate,
    MonitoringAccountWithLoginSessionCreate,
    MonitoringAccountWithLoginSessionResponse,
)
from app.services import monitoring_accounts as service
from app.services.monitoring_accounts import (
    BrowserProfileNotFound,
    CookieStateNotFound,
    MonitoringAccountAlreadyExists,
    MonitoringAccountNotFound,
)
from app.streams import EVT_LOGIN_SESSION_CREATED, EVT_LOGIN_SESSION_RUNNING, WEB_EVENTS, StreamClient
from app.streams.messages import WebEventPayload, encode_payload

router = APIRouter()


@router.get("", response_model=PaginatedResponse[MonitoringAccountResponse])
async def list_monitoring_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.get_monitoring_accounts(page=page, page_size=page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=MonitoringAccountResponse, status_code=201)
async def create_monitoring_account(data: MonitoringAccountCreate):
    try:
        account = await service.create_monitoring_account(data)
    except MonitoringAccountAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return account


@router.post("/with-login-session", response_model=MonitoringAccountWithLoginSessionResponse, status_code=201)
async def create_with_login_session(data: MonitoringAccountWithLoginSessionCreate):
    try:
        account, profile, login_session, vnc_url = (
            await service.create_monitoring_account_with_login_session(data)
        )
    except MonitoringAccountAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    redis = await get_redis()
    client = StreamClient(redis)

    created_payload = WebEventPayload(
        type=EVT_LOGIN_SESSION_CREATED,
        payload={"session_id": str(login_session.id), "status": "pending"},
    )
    await client.xadd(WEB_EVENTS, encode_payload(created_payload))

    running_payload = WebEventPayload(
        type=EVT_LOGIN_SESSION_RUNNING,
        payload={"session_id": str(login_session.id), "status": "running"},
    )
    await client.xadd(WEB_EVENTS, encode_payload(running_payload))

    return MonitoringAccountWithLoginSessionResponse(
        account=MonitoringAccountResponse.model_validate(account),
        browser_profile=profile,
        login_session=login_session,
        vnc_url=vnc_url,
    )


@router.post("/{account_id}/cookies/import", response_model=CookieImportResponse)
async def import_cookies(account_id: uuid.UUID, data: CookieImportRequest):
    try:
        account, profile, health = await service.import_monitoring_account_cookies(
            account_id,
            data.model_dump(),
        )
    except MonitoringAccountNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CookieImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await _emit_account_event(
        "account.cookie_imported",
        {"account_id": str(account.id), "profile_id": str(profile.id), "status": health.status.value},
    )
    await _emit_account_event(
        "account.health_check.completed",
        {
            "account_id": str(account.id),
            "profile_id": str(profile.id),
            "status": health.status.value,
            "reason": health.reason,
        },
    )

    return CookieImportResponse(
        account=MonitoringAccountResponse.model_validate(account),
        browser_profile=profile,
        health_check=LoginHealthResponse(**health.to_dict()),
    )


@router.post("/{account_id}/health-check", response_model=MonitoringAccountHealthCheckResponse)
async def check_login_state(account_id: uuid.UUID):
    try:
        account, profile, health = await service.check_monitoring_account_login_state(account_id)
    except MonitoringAccountNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except BrowserProfileNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CookieStateNotFound as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    await _emit_account_event(
        "account.health_check.completed",
        {
            "account_id": str(account.id),
            "profile_id": str(profile.id),
            "status": health.status.value,
            "reason": health.reason,
        },
    )

    return MonitoringAccountHealthCheckResponse(
        account=MonitoringAccountResponse.model_validate(account),
        browser_profile=profile,
        health_check=LoginHealthResponse(**health.to_dict()),
    )


@router.patch("/{account_id}", response_model=MonitoringAccountResponse)
async def update_monitoring_account(account_id: uuid.UUID, data: MonitoringAccountUpdate):
    account = await service.update_monitoring_account(account_id, data)
    if account is None:
        raise HTTPException(status_code=404, detail="Monitoring account not found")
    return account


@router.delete("/{account_id}", status_code=204)
async def delete_monitoring_account(account_id: uuid.UUID):
    deleted = await service.delete_monitoring_account(account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Monitoring account not found")


async def _emit_account_event(event_type: str, payload: dict) -> None:
    redis = await get_redis()
    client = StreamClient(redis)
    await client.xadd(WEB_EVENTS, encode_payload(WebEventPayload(type=event_type, payload=payload)))
