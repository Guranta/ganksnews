import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitoringAccount


async def get_by_id(db: AsyncSession, account_id: uuid.UUID) -> MonitoringAccount | None:
    result = await db.execute(select(MonitoringAccount).where(MonitoringAccount.id == account_id))
    return result.scalar_one_or_none()


async def get_by_username(db: AsyncSession, platform: str, username: str) -> MonitoringAccount | None:
    result = await db.execute(
        select(MonitoringAccount).where(MonitoringAccount.platform == platform, MonitoringAccount.username == username)
    )
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[MonitoringAccount], int]:
    count_result = await db.execute(select(func.count()).select_from(MonitoringAccount))
    total = count_result.scalar_one()

    query = (
        select(MonitoringAccount)
        .order_by(MonitoringAccount.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def create(db: AsyncSession, **kwargs) -> MonitoringAccount:
    account = MonitoringAccount(**kwargs)
    db.add(account)
    await db.flush()
    return account


async def update(db: AsyncSession, account: MonitoringAccount, **kwargs) -> MonitoringAccount:
    for key, value in kwargs.items():
        if value is not None:
            setattr(account, key, value)
    await db.flush()
    return account


async def delete(db: AsyncSession, account: MonitoringAccount) -> None:
    await db.delete(account)
    await db.flush()
