import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitorList, MonitorListMembership


async def get_by_id(db: AsyncSession, list_id: uuid.UUID) -> MonitorList | None:
    result = await db.execute(select(MonitorList).where(MonitorList.id == list_id))
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[MonitorList]:
    result = await db.execute(select(MonitorList).order_by(MonitorList.created_at.desc()))
    return result.scalars().all()


async def create(db: AsyncSession, **kwargs) -> MonitorList:
    monitor_list = MonitorList(**kwargs)
    db.add(monitor_list)
    await db.flush()
    return monitor_list


async def update(db: AsyncSession, monitor_list: MonitorList, **kwargs) -> MonitorList:
    for key, value in kwargs.items():
        if value is not None:
            setattr(monitor_list, key, value)
    await db.flush()
    return monitor_list


async def delete(db: AsyncSession, monitor_list: MonitorList) -> None:
    await db.delete(monitor_list)
    await db.flush()


async def add_member(db: AsyncSession, monitor_list_id: uuid.UUID, target_account_id: uuid.UUID) -> MonitorListMembership:
    membership = MonitorListMembership(monitor_list_id=monitor_list_id, target_account_id=target_account_id)
    db.add(membership)
    await db.flush()
    return membership


async def remove_member(db: AsyncSession, monitor_list_id: uuid.UUID, target_account_id: uuid.UUID) -> None:
    result = await db.execute(
        select(MonitorListMembership).where(
            MonitorListMembership.monitor_list_id == monitor_list_id,
            MonitorListMembership.target_account_id == target_account_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        await db.delete(membership)
        await db.flush()


async def list_members(db: AsyncSession, monitor_list_id: uuid.UUID) -> list[MonitorListMembership]:
    result = await db.execute(
        select(MonitorListMembership).where(MonitorListMembership.monitor_list_id == monitor_list_id)
    )
    return result.scalars().all()
