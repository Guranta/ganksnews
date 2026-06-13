from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.redis import get_redis
from app.models import BrowserProfile
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

LOCK_PREFIX = "lgn:profile_lock:"
DEFAULT_LOCK_TTL_SECONDS = 300


def _lock_key(profile_id: uuid.UUID) -> str:
    return f"{LOCK_PREFIX}{profile_id}"


async def acquire_lock(
    profile_id: uuid.UUID,
    worker_id: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> bool:
    redis = await get_redis()
    key = _lock_key(profile_id)
    acquired = await redis.set(key, worker_id, nx=True, ex=ttl_seconds)
    if acquired:
        async with async_session_factory() as db:
            await db.execute(
                update(BrowserProfile)
                .where(BrowserProfile.id == profile_id)
                .values(locked_by=worker_id, locked_at=datetime.now(timezone.utc))
            )
            await db.commit()
        logger.info("Profile %s locked by %s", profile_id, worker_id)
    return bool(acquired)


async def release_lock(profile_id: uuid.UUID, worker_id: str) -> bool:
    redis = await get_redis()
    key = _lock_key(profile_id)
    current = await redis.get(key)
    if current and current != worker_id:
        logger.warning("Profile %s lock owned by %s, not %s — cannot release", profile_id, current, worker_id)
        return False
    released = await redis.delete(key)
    if released:
        async with async_session_factory() as db:
            await db.execute(
                update(BrowserProfile)
                .where(BrowserProfile.id == profile_id)
                .values(locked_by=None, locked_at=None)
            )
            await db.commit()
        logger.info("Profile %s unlocked by %s", profile_id, worker_id)
    return bool(released)


async def extend_lock(profile_id: uuid.UUID, worker_id: str, ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS) -> bool:
    redis = await get_redis()
    key = _lock_key(profile_id)
    current = await redis.get(key)
    if current != worker_id:
        return False
    await redis.expire(key, ttl_seconds)
    return True


async def is_locked(profile_id: uuid.UUID) -> bool:
    redis = await get_redis()
    key = _lock_key(profile_id)
    return bool(await redis.exists(key))


async def get_lock_owner(profile_id: uuid.UUID) -> str | None:
    redis = await get_redis()
    key = _lock_key(profile_id)
    return await redis.get(key)


async def cleanup_stale_locks(stale_threshold_seconds: int = 600) -> int:
    redis = await get_redis()
    cursor = 0
    cleaned = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=f"{LOCK_PREFIX}*", count=100)
        for key in keys:
            profile_id_str = key.replace(LOCK_PREFIX, "")
            try:
                profile_uuid = uuid.UUID(profile_id_str)
            except ValueError:
                continue

            ttl = await redis.ttl(key)
            if ttl is not None and ttl < 0:
                async with async_session_factory() as db:
                    await db.execute(
                        update(BrowserProfile)
                        .where(BrowserProfile.id == profile_uuid)
                        .values(locked_by=None, locked_at=None)
                    )
                    await db.commit()
                await redis.delete(key)
                cleaned += 1
                logger.info("Cleaned stale lock for profile %s", profile_uuid)

        if cursor == 0:
            break

    async with async_session_factory() as db:
        result = await db.execute(
            update(BrowserProfile)
            .where(
                BrowserProfile.locked_by.isnot(None),
                BrowserProfile.locked_at < datetime.now(timezone.utc) - timedelta(seconds=stale_threshold_seconds),
            )
            .values(locked_by=None, locked_at=None)
        )
        await db.commit()
        cleaned += result.rowcount

    if cleaned:
        logger.info("Stale lock cleanup: %d locks removed", cleaned)
    return cleaned
