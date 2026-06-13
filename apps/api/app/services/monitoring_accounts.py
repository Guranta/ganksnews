import logging
import uuid

from sqlalchemy.exc import IntegrityError

from app.core.database import async_session_factory
from app.models import MonitoringAccountStatus
from app.repositories import monitoring_accounts as repo
from app.schemas.monitoring_accounts import MonitoringAccountCreate, MonitoringAccountUpdate

logger = logging.getLogger(__name__)


class MonitoringAccountAlreadyExists(Exception):
    pass


def normalize_username(username: str) -> str:
    return username.strip().lstrip("@")


async def get_monitoring_accounts(page: int = 1, page_size: int = 20):
    async with async_session_factory() as db:
        return await repo.list_all(db, page=page, page_size=page_size)


async def get_monitoring_account(account_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, account_id)


async def create_monitoring_account(data: MonitoringAccountCreate):
    async with async_session_factory() as db:
        username = normalize_username(data.username)
        if not username:
            raise ValueError("Username is required")

        existing = await repo.get_by_username(db, platform="twitter", username=username)
        if existing:
            raise MonitoringAccountAlreadyExists(
                f"Monitoring account already exists for platform=twitter username={username}"
            )

        create_kwargs = data.model_dump()
        create_kwargs["username"] = username
        create_kwargs["platform"] = "twitter"
        create_kwargs["status"] = MonitoringAccountStatus.NEEDS_LOGIN

        try:
            account = await repo.create(db, **create_kwargs)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise MonitoringAccountAlreadyExists(
                f"Monitoring account already exists for platform=twitter username={username}"
            )

        logger.info("Monitoring account created id=%s username=%s status=needs_login", account.id, username)
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
