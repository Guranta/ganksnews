from app.core.database import async_session_factory
from app.repositories import dashboard as repo


async def get_summary():
    async with async_session_factory() as db:
        return await repo.get_summary(db)
