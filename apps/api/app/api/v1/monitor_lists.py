import uuid

from fastapi import APIRouter, HTTPException

from app.schemas.monitor_lists import (
    MonitorListCreate,
    MonitorListMembershipCreate,
    MonitorListMembershipResponse,
    MonitorListResponse,
    MonitorListUpdate,
)
from app.services import monitor_lists as service

router = APIRouter()


@router.get("", response_model=list[MonitorListResponse])
async def list_monitor_lists():
    return await service.get_monitor_lists()


@router.post("", response_model=MonitorListResponse, status_code=201)
async def create_monitor_list(data: MonitorListCreate):
    return await service.create_monitor_list(data)


@router.get("/{list_id}/members", response_model=list[MonitorListMembershipResponse])
async def list_members(list_id: uuid.UUID):
    monitor_list = await service.get_monitor_list(list_id)
    if monitor_list is None:
        raise HTTPException(status_code=404, detail="Monitor list not found")
    return await service.list_members(list_id)


@router.post("/{list_id}/members", response_model=MonitorListMembershipResponse, status_code=201)
async def add_member(list_id: uuid.UUID, data: MonitorListMembershipCreate):
    monitor_list = await service.get_monitor_list(list_id)
    if monitor_list is None:
        raise HTTPException(status_code=404, detail="Monitor list not found")
    return await service.add_member(list_id, data.target_account_id)


@router.delete("/{list_id}/members/{target_account_id}", status_code=204)
async def remove_member(list_id: uuid.UUID, target_account_id: uuid.UUID):
    await service.remove_member(list_id, target_account_id)
