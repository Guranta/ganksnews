from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum

from app.core.database import async_session_factory
from app.core.redis import get_redis
from app.models import BrowserProfile, MonitoringAccount
from app.streams import StreamClient, ACCOUNT_EVENTS, EVT_ACCOUNT_STATUS, EVT_PROFILE_ERROR, stream_key
from app.streams.messages import encode_payload, WebEventPayload
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class ProfileHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AccountHealth(str, Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    SUSPENDED = "suspended"
    LOGGED_OUT = "logged_out"
    UNKNOWN = "unknown"


async def check_profile_health(profile_id: uuid.UUID) -> ProfileHealth:
    async with async_session_factory() as db:
        result = await db.execute(select(BrowserProfile).where(BrowserProfile.id == profile_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            return ProfileHealth.UNKNOWN

        health = ProfileHealth.HEALTHY

        if profile.locked_by and profile.locked_at:
            lock_age = (datetime.now(timezone.utc) - profile.locked_at).total_seconds()
            if lock_age > 600:
                health = ProfileHealth.DEGRADED

        if profile.last_health_check_at:
            check_age = (datetime.now(timezone.utc) - profile.last_health_check_at).total_seconds()
            if check_age > 3600:
                health = ProfileHealth.DEGRADED

        await db.execute(
            update(BrowserProfile)
            .where(BrowserProfile.id == profile_id)
            .values(last_health_check_at=datetime.now(timezone.utc))
        )
        await db.commit()

    await _emit_profile_event(profile_id, health)
    return health


async def check_account_health(account_id: uuid.UUID) -> AccountHealth:
    async with async_session_factory() as db:
        result = await db.execute(select(MonitoringAccount).where(MonitoringAccount.id == account_id))
        account = result.scalar_one_or_none()
        if account is None:
            return AccountHealth.UNKNOWN

        health = AccountHealth.ACTIVE

        if account.status == "suspended":
            health = AccountHealth.SUSPENDED
        elif account.status == "rate_limited":
            health = AccountHealth.RATE_LIMITED
        elif account.status == "logged_out":
            health = AccountHealth.LOGGED_OUT

    await _emit_account_event(account_id, health)
    return health


async def check_all_profiles() -> dict[str, int]:
    async with async_session_factory() as db:
        result = await db.execute(select(BrowserProfile))
        profiles = result.scalars().all()

    counts: dict[str, int] = {h.value: 0 for h in ProfileHealth}
    for profile in profiles:
        health = await check_profile_health(profile.id)
        counts[health.value] += 1
    return counts


async def check_all_accounts() -> dict[str, int]:
    async with async_session_factory() as db:
        result = await db.execute(select(MonitoringAccount))
        accounts = result.scalars().all()

    counts: dict[str, int] = {h.value: 0 for h in AccountHealth}
    for account in accounts:
        health = await check_account_health(account.id)
        counts[health.value] += 1
    return counts


async def save_artifact_error(
    crawl_job_id: uuid.UUID,
    error_trace: str,
    raw_payload: str | None = None,
) -> None:
    from app.models import Artifact, ArtifactType

    async with async_session_factory() as db:
        artifact = Artifact(
            crawl_job_id=crawl_job_id,
            artifact_type=ArtifactType.error_trace,
            content=error_trace,
            raw_payload=raw_payload,
        )
        db.add(artifact)
        await db.commit()
    logger.info("Saved error artifact for job %s", crawl_job_id)


async def _emit_profile_event(profile_id: uuid.UUID, health: ProfileHealth) -> None:
    redis = await get_redis()
    client = StreamClient(redis)
    payload = WebEventPayload(
        type=EVT_PROFILE_ERROR,
        payload={"profile_id": str(profile_id), "health": health.value},
    )
    await client.xadd(ACCOUNT_EVENTS, encode_payload(payload))


async def _emit_account_event(account_id: uuid.UUID, health: AccountHealth) -> None:
    redis = await get_redis()
    client = StreamClient(redis)
    payload = WebEventPayload(
        type=EVT_ACCOUNT_STATUS,
        payload={"account_id": str(account_id), "health": health.value},
    )
    await client.xadd(ACCOUNT_EVENTS, encode_payload(payload))
