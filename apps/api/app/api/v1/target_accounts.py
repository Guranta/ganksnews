import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db
from app.models import TargetAccountStatus
from app.schemas.common import PaginatedResponse
from app.schemas.target_accounts import (
    TargetAccountBulkImportRequest,
    TargetAccountBulkImportResponse,
    TargetAccountCreate,
    TargetAccountResponse,
    TargetAccountUpdate,
)
from app.services import target_accounts as service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TargetAccountResponse])
async def list_target_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: TargetAccountStatus | None = None,
    search: str | None = None,
):
    items, total = await service.get_target_accounts(page=page, page_size=page_size, status=status, search=search)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TargetAccountResponse, status_code=201)
async def create_target_account(data: TargetAccountCreate):
    account = await service.create_target_account(data)
    return account


@router.post("/import", response_model=TargetAccountBulkImportResponse)
async def bulk_import_target_accounts(data: TargetAccountBulkImportRequest):
    batch = await service.bulk_import_target_accounts(data)
    return batch


@router.patch("/{account_id}", response_model=TargetAccountResponse)
async def update_target_account(account_id: uuid.UUID, data: TargetAccountUpdate):
    account = await service.update_target_account(account_id, data)
    if account is None:
        raise HTTPException(status_code=404, detail="Target account not found")
    return account


@router.delete("/{account_id}", status_code=204)
async def delete_target_account(account_id: uuid.UUID):
    deleted = await service.delete_target_account(account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Target account not found")
