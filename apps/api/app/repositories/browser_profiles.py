import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BrowserProfile


async def get_by_id(db: AsyncSession, profile_id: uuid.UUID) -> BrowserProfile | None:
    result = await db.execute(select(BrowserProfile).where(BrowserProfile.id == profile_id))
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[BrowserProfile], int]:
    count_result = await db.execute(select(func.count()).select_from(BrowserProfile))
    total = count_result.scalar_one()

    query = (
        select(BrowserProfile)
        .order_by(BrowserProfile.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def create(db: AsyncSession, **kwargs) -> BrowserProfile:
    profile = BrowserProfile(**kwargs)
    db.add(profile)
    await db.flush()
    return profile


async def update(db: AsyncSession, profile: BrowserProfile, **kwargs) -> BrowserProfile:
    for key, value in kwargs.items():
        if value is not None:
            setattr(profile, key, value)
    await db.flush()
    return profile


async def delete(db: AsyncSession, profile: BrowserProfile) -> None:
    await db.delete(profile)
    await db.flush()
