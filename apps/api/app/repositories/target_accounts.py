import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models import TargetAccount, TargetAccountImportBatch, TargetAccountStatus


async def get_by_id(db: AsyncSession, account_id: uuid.UUID) -> TargetAccount | None:
    result = await db.execute(select(TargetAccount).where(TargetAccount.id == account_id))
    return result.scalar_one_or_none()


async def get_by_username(db: AsyncSession, platform: str, username: str) -> TargetAccount | None:
    result = await db.execute(
        select(TargetAccount).where(TargetAccount.platform == platform, TargetAccount.username == username)
    )
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: TargetAccountStatus | None = None,
    search: str | None = None,
) -> tuple[list[TargetAccount], int]:
    query = select(TargetAccount)
    count_query = select(func.count()).select_from(TargetAccount)

    if status is not None:
        query = query.where(TargetAccount.status == status)
        count_query = count_query.where(TargetAccount.status == status)

    if search:
        pattern = f"%{search}%"
        search_filter = TargetAccount.username.ilike(pattern) | TargetAccount.display_name.ilike(pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(TargetAccount.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def create(db: AsyncSession, **kwargs) -> TargetAccount:
    account = TargetAccount(**kwargs)
    db.add(account)
    await db.flush()
    return account


async def update(db: AsyncSession, account: TargetAccount, **kwargs) -> TargetAccount:
    for key, value in kwargs.items():
        if value is not None:
            setattr(account, key, value)
    await db.flush()
    return account


async def delete(db: AsyncSession, account: TargetAccount) -> None:
    await db.delete(account)
    await db.flush()


async def bulk_import(db: AsyncSession, text: str, platform: str = "twitter") -> TargetAccountImportBatch:
    lines = [line.strip().lstrip("@") for line in text.splitlines()]
    usernames = [u for u in lines if u]

    created_count = 0
    updated_count = 0
    failed_count = 0
    errors: list[str] = []

    for username in usernames:
        try:
            stmt = insert(TargetAccount).values(platform=platform, username=username)
            stmt = stmt.on_conflict_do_update(
                constraint="target_accounts_platform_username_key",
                set_={"username": stmt.excluded.username},
            )
            result = await db.execute(stmt)

            if result.rowcount == 1:
                created_count += 1
            else:
                updated_count += 1
        except Exception as e:
            failed_count += 1
            errors.append(f"{username}: {str(e)}")

    batch = TargetAccountImportBatch(
        total_count=len(usernames),
        created_count=created_count,
        updated_count=updated_count,
        failed_count=failed_count,
        errors=errors if errors else None,
    )
    db.add(batch)
    await db.flush()
    return batch
