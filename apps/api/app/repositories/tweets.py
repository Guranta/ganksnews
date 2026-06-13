import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tweet


async def get_by_id(db: AsyncSession, tweet_id: uuid.UUID) -> Tweet | None:
    result = await db.execute(select(Tweet).where(Tweet.id == tweet_id))
    return result.scalar_one_or_none()


async def get_by_tweet_id(db: AsyncSession, platform: str, tweet_id: str) -> Tweet | None:
    result = await db.execute(
        select(Tweet).where(Tweet.platform == platform, Tweet.tweet_id == tweet_id)
    )
    return result.scalar_one_or_none()


async def list_latest(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    author: str | None = None,
    search: str | None = None,
) -> tuple[list[Tweet], int]:
    query = select(Tweet)
    count_query = select(func.count()).select_from(Tweet)

    if author:
        query = query.where(Tweet.author_username.ilike(f"%{author}%"))
        count_query = count_query.where(Tweet.author_username.ilike(f"%{author}%"))

    if search:
        pattern = f"%{search}%"
        search_filter = Tweet.text.ilike(pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Tweet.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total
