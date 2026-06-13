import uuid

from app.core.database import async_session_factory
from app.models import LoginSessionStatus
from app.repositories import login_sessions as repo
from app.schemas.login_sessions import LoginSessionCreate, LoginSessionUpdate


async def get_login_sessions(
    page: int = 1, page_size: int = 20, status: LoginSessionStatus | None = None
):
    async with async_session_factory() as db:
        return await repo.list_all(db, page=page, page_size=page_size, status=status)


async def get_login_session(session_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, session_id)


async def create_login_session(data: LoginSessionCreate):
    async with async_session_factory() as db:
        session = await repo.create(db, **data.model_dump())
        await db.commit()
        return session


async def update_login_session_status(
    session_id: uuid.UUID,
    status: LoginSessionStatus,
    error_message: str | None = None,
):
    async with async_session_factory() as db:
        session = await repo.update_status(db, session_id, status, error_message=error_message)
        if session is None:
            return None
        await db.commit()
        return session
