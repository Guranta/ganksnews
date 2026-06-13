import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LoginSession, LoginSessionStatus


async def get_by_id(db: AsyncSession, session_id: uuid.UUID) -> LoginSession | None:
    result = await db.execute(select(LoginSession).where(LoginSession.id == session_id))
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: LoginSessionStatus | None = None,
) -> tuple[list[LoginSession], int]:
    query = select(LoginSession)
    count_query = select(func.count()).select_from(LoginSession)

    if status is not None:
        query = query.where(LoginSession.status == status)
        count_query = count_query.where(LoginSession.status == status)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(LoginSession.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def count_by_status(db: AsyncSession, status: LoginSessionStatus) -> int:
    result = await db.execute(
        select(func.count()).select_from(LoginSession).where(LoginSession.status == status)
    )
    return result.scalar_one()


async def find_running_with_token_hash(db: AsyncSession) -> list[LoginSession]:
    result = await db.execute(
        select(LoginSession).where(LoginSession.status == LoginSessionStatus.RUNNING)
    )
    sessions = result.scalars().all()
    return [s for s in sessions if s.extra_data and "novnc_token_hash" in s.extra_data]


async def create(db: AsyncSession, **kwargs) -> LoginSession:
    session = LoginSession(**kwargs)
    db.add(session)
    await db.flush()
    return session


async def update_status(
    db: AsyncSession,
    session_id: uuid.UUID,
    status: LoginSessionStatus,
    error_message: str | None = None,
    extra_data: dict | None = None,
) -> LoginSession | None:
    session = await get_by_id(db, session_id)
    if session is None:
        return None
    session.status = status
    if error_message:
        session.error_message = error_message
    if extra_data is not None:
        session.extra_data = extra_data
    if status == LoginSessionStatus.RUNNING and session.started_at is None:
        session.started_at = datetime.now(timezone.utc)
    if status in (LoginSessionStatus.COMPLETED, LoginSessionStatus.FAILED, LoginSessionStatus.CANCELLED):
        session.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return session
