import uuid

from app.core.database import async_session_factory
from app.repositories import monitoring_accounts as repo
from app.schemas.monitoring_accounts import MonitoringAccountCreate, MonitoringAccountUpdate


async def get_monitoring_accounts(page: int = 1, page_size: int = 20):
    async with async_session_factory() as db:
        return await repo.list_all(db, page=page, page_size=page_size)


async def get_monitoring_account(account_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, account_id)


async def create_monitoring_account(data: MonitoringAccountCreate):
    async with async_session_factory() as db:
        account = await repo.create(db, **data.model_dump())
        await db.commit()
        return account


async def update_monitoring_account(account_id: uuid.UUID, data: MonitoringAccountUpdate):
    async with async_session_factory() as db:
        account = await repo.get_by_id(db, account_id)
        if account is None:
            return None
        account = await repo.update(db, account, **data.model_dump(exclude_unset=True))
        await db.commit()
        return account


async def delete_monitoring_account(account_id: uuid.UUID):
    async with async_session_factory() as db:
        account = await repo.get_by_id(db, account_id)
        if account is None:
            return False
        await repo.delete(db, account)
        await db.commit()
        return True
