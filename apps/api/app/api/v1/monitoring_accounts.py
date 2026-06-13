import uuid

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.common import PaginatedResponse
from app.schemas.monitoring_accounts import (
    MonitoringAccountCreate,
    MonitoringAccountResponse,
    MonitoringAccountUpdate,
    MonitoringAccountWithLoginSessionCreate,
    MonitoringAccountWithLoginSessionResponse,
)
from app.services import monitoring_accounts as service
from app.services.monitoring_accounts import MonitoringAccountAlreadyExists
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
