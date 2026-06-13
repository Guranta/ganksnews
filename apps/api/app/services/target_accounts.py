import uuid

from app.core.database import async_session_factory
from app.models import TargetAccountStatus
from app.repositories import target_accounts as repo
from app.schemas.target_accounts import TargetAccountBulkImportRequest, TargetAccountCreate, TargetAccountUpdate


async def get_target_accounts(
    page: int = 1, page_size: int = 20, status: TargetAccountStatus | None = None, search: str | None = None
):
    async with async_session_factory() as db:
        return await repo.list_all(db, page=page, page_size=page_size, status=status, search=search)


async def get_target_account(account_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, account_id)


async def create_target_account(data: TargetAccountCreate):
    async with async_session_factory() as db:
        account = await repo.create(db, **data.model_dump())
        await db.commit()
        return account


async def update_target_account(account_id: uuid.UUID, data: TargetAccountUpdate):
    async with async_session_factory() as db:
        account = await repo.get_by_id(db, account_id)
        if account is None:
            return None
        account = await repo.update(db, account, **data.model_dump(exclude_unset=True))
        await db.commit()
        return account


async def delete_target_account(account_id: uuid.UUID):
    async with async_session_factory() as db:
        account = await repo.get_by_id(db, account_id)
        if account is None:
            return False
        await repo.delete(db, account)
        await db.commit()
        return True


async def bulk_import_target_accounts(data: TargetAccountBulkImportRequest):
    async with async_session_factory() as db:
        batch = await repo.bulk_import(db, data.text)
        await db.commit()
        return {
            "batch_id": batch.id,
            "total_count": batch.total_count,
            "created_count": batch.created_count,
            "updated_count": batch.updated_count,
            "failed_count": batch.failed_count,
            "errors": batch.errors,
        }
