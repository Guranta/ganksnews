import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db
from app.schemas.browser_profiles import (
    BrowserProfileCreate,
    BrowserProfileResponse,
    BrowserProfileUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services import browser_profiles as service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[BrowserProfileResponse])
async def list_browser_profiles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await service.get_browser_profiles(page=page, page_size=page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=BrowserProfileResponse, status_code=201)
async def create_browser_profile(data: BrowserProfileCreate):
    profile = await service.create_browser_profile(data)
    return profile


@router.patch("/{profile_id}", response_model=BrowserProfileResponse)
async def update_browser_profile(profile_id: uuid.UUID, data: BrowserProfileUpdate):
    profile = await service.update_browser_profile(profile_id, data)
    if profile is None:
        raise HTTPException(status_code=404, detail="Browser profile not found")
    return profile


@router.delete("/{profile_id}", status_code=204)
async def delete_browser_profile(profile_id: uuid.UUID):
    deleted = await service.delete_browser_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Browser profile not found")
