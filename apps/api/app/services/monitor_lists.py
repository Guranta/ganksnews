import uuid

from app.core.database import async_session_factory
from app.repositories import monitor_lists as repo
from app.schemas.monitor_lists import MonitorListCreate, MonitorListUpdate


async def get_monitor_lists():
    async with async_session_factory() as db:
        return await repo.list_all(db)


async def get_monitor_list(list_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, list_id)


async def create_monitor_list(data: MonitorListCreate):
    async with async_session_factory() as db:
        monitor_list = await repo.create(db, **data.model_dump())
        await db.commit()
        return monitor_list


async def update_monitor_list(list_id: uuid.UUID, data: MonitorListUpdate):
    async with async_session_factory() as db:
        monitor_list = await repo.get_by_id(db, list_id)
        if monitor_list is None:
            return None
        monitor_list = await repo.update(db, monitor_list, **data.model_dump(exclude_unset=True))
        await db.commit()
        return monitor_list


async def delete_monitor_list(list_id: uuid.UUID):
    async with async_session_factory() as db:
        monitor_list = await repo.get_by_id(db, list_id)
        if monitor_list is None:
            return False
        await repo.delete(db, monitor_list)
        await db.commit()
        return True


async def add_member(list_id: uuid.UUID, target_account_id: uuid.UUID):
    async with async_session_factory() as db:
        membership = await repo.add_member(db, list_id, target_account_id)
        await db.commit()
        return membership


async def remove_member(list_id: uuid.UUID, target_account_id: uuid.UUID):
    async with async_session_factory() as db:
        await repo.remove_member(db, list_id, target_account_id)
        await db.commit()


async def list_members(list_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.list_members(db, list_id)
