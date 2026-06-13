import uuid

from app.core.database import async_session_factory
from app.repositories import tweets as repo


async def get_latest_tweets(
    page: int = 1, page_size: int = 20, author: str | None = None, search: str | None = None
):
    async with async_session_factory() as db:
        return await repo.list_latest(db, page=page, page_size=page_size, author=author, search=search)


async def get_tweet(tweet_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, tweet_id)
