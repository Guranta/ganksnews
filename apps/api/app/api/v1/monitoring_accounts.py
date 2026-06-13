import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.monitoring_accounts import (
    MonitoringAccountCreate,
    MonitoringAccountResponse,
    MonitoringAccountUpdate,
)
from app.services import monitoring_accounts as service

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
    account = await service.create_monitoring_account(data)
    return account


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
