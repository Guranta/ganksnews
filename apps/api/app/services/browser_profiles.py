import uuid

from app.core.database import async_session_factory
from app.repositories import browser_profiles as repo
from app.repositories import login_sessions as ls_repo
from app.schemas.browser_profiles import BrowserProfileCreate, BrowserProfileUpdate


async def get_browser_profiles(page: int = 1, page_size: int = 20):
    async with async_session_factory() as db:
        return await repo.list_all(db, page=page, page_size=page_size)


async def get_browser_profile(profile_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, profile_id)


async def create_browser_profile(data: BrowserProfileCreate):
    async with async_session_factory() as db:
        profile = await repo.create(db, **data.model_dump())
        await db.commit()
        return profile


async def update_browser_profile(profile_id: uuid.UUID, data: BrowserProfileUpdate):
    async with async_session_factory() as db:
        profile = await repo.get_by_id(db, profile_id)
        if profile is None:
            return None
        profile = await repo.update(db, profile, **data.model_dump(exclude_unset=True))
        await db.commit()
        return profile


async def delete_browser_profile(profile_id: uuid.UUID):
    async with async_session_factory() as db:
        profile = await repo.get_by_id(db, profile_id)
        if profile is None:
            return False
        await ls_repo.delete_by_browser_profile(db, profile_id)
        await repo.delete(db, profile)
        await db.commit()
        return True
