from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, update

from app.browser.cookies import BrowserCookie
from app.browser.storage_state import write_health_summary
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.redis import get_redis
from app.models import BrowserProfile, BrowserProfileStatus, MonitoringAccount, MonitoringAccountStatus
from app.streams import ACCOUNT_EVENTS, EVT_ACCOUNT_STATUS, EVT_PROFILE_ERROR, StreamClient
from app.streams.messages import WebEventPayload, encode_payload

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


@dataclass(frozen=True)
class LoginHealthResult:
    status: MonitoringAccountStatus
    profile_status: BrowserProfileStatus
    reason: str
    checked_at: datetime
    final_url: str | None = None
    http_status: int | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "profile_status": self.profile_status.value,
            "reason": self.reason,
            "checked_at": self.checked_at.isoformat(),
            "final_url": self.final_url,
            "http_status": self.http_status,
            "duration_ms": self.duration_ms,
        }


async def check_twitter_cookie_login_state(
    profile: BrowserProfile,
    cookies: list[BrowserCookie],
) -> LoginHealthResult:
    started = datetime.now(UTC)
    cookie_header = "; ".join(f"{cookie.name}={cookie.value}" for cookie in cookies)
    headers = {
        "Cookie": cookie_header,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        timeout = min(settings.BROWSER_DEFAULT_TIMEOUT_MS / 1000, 20)
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(settings.X_LOGIN_CHECK_URL, headers=headers)
    except httpx.HTTPError as exc:
        result = _login_health_result(
            MonitoringAccountStatus.NEEDS_LOGIN,
            BrowserProfileStatus.ERROR,
            "browser_or_network_error",
            started,
            final_url=None,
            http_status=None,
        )
        write_health_summary(profile, {**result.to_dict(), "error": exc.__class__.__name__})
        return result

    result = _classify_login_response(response, started)
    write_health_summary(profile, result.to_dict())
    return result


def apply_login_health_result(
    account: MonitoringAccount,
    profile: BrowserProfile,
    result: LoginHealthResult,
) -> None:
    account.status = result.status
    account.last_login_check_at = result.checked_at
    profile.status = result.profile_status
    profile.last_health_check_at = result.checked_at


def _classify_login_response(response: httpx.Response, started: datetime) -> LoginHealthResult:
    final_url = str(response.url)
    parsed = urlparse(final_url)
    body = response.text[:20000].lower()

    if response.status_code == 429:
        return _login_health_result(
            MonitoringAccountStatus.CHALLENGED,
            BrowserProfileStatus.NEEDS_LOGIN,
            "rate_limited",
            started,
            final_url=final_url,
            http_status=response.status_code,
        )

    if response.status_code >= 500:
        return _login_health_result(
            MonitoringAccountStatus.NEEDS_LOGIN,
            BrowserProfileStatus.ERROR,
            "browser_or_network_error",
            started,
            final_url=final_url,
            http_status=response.status_code,
        )

    if "suspended" in body or "account suspended" in body:
        return _login_health_result(
            MonitoringAccountStatus.SUSPENDED,
            BrowserProfileStatus.NEEDS_LOGIN,
            "account_suspended",
            started,
            final_url=final_url,
            http_status=response.status_code,
        )

    if any(marker in body for marker in ("challenge", "unlock", "captcha", "verify your identity")):
        return _login_health_result(
            MonitoringAccountStatus.CHALLENGED,
            BrowserProfileStatus.NEEDS_LOGIN,
            "challenge_seen",
            started,
            final_url=final_url,
            http_status=response.status_code,
        )

    if parsed.path in {"/home", "/i/timeline"} and response.status_code < 400:
        return _login_health_result(
            MonitoringAccountStatus.ACTIVE,
            BrowserProfileStatus.AVAILABLE,
            "home_accessible",
            started,
            final_url=final_url,
            http_status=response.status_code,
        )

    if "/login" in parsed.path or "/i/flow/login" in parsed.path or "sign in to x" in body:
        return _login_health_result(
            MonitoringAccountStatus.NEEDS_LOGIN,
            BrowserProfileStatus.NEEDS_LOGIN,
            "redirected_to_login",
            started,
            final_url=final_url,
            http_status=response.status_code,
        )

    return _login_health_result(
        MonitoringAccountStatus.NEEDS_LOGIN,
        BrowserProfileStatus.NEEDS_LOGIN,
        "unknown_state",
        started,
        final_url=final_url,
        http_status=response.status_code,
    )


def _login_health_result(
    status: MonitoringAccountStatus,
    profile_status: BrowserProfileStatus,
    reason: str,
    started: datetime,
    *,
    final_url: str | None,
    http_status: int | None,
) -> LoginHealthResult:
    checked_at = datetime.now(UTC)
    duration_ms = int((checked_at - started).total_seconds() * 1000)
    return LoginHealthResult(
        status=status,
        profile_status=profile_status,
        reason=reason,
        checked_at=checked_at,
        final_url=final_url,
        http_status=http_status,
        duration_ms=duration_ms,
    )


async def check_profile_health(profile_id: uuid.UUID) -> ProfileHealth:
    async with async_session_factory() as db:
        result = await db.execute(select(BrowserProfile).where(BrowserProfile.id == profile_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            return ProfileHealth.UNKNOWN

        health = ProfileHealth.HEALTHY

        if profile.locked_by and profile.locked_at:
            lock_age = (datetime.now(UTC) - profile.locked_at).total_seconds()
            if lock_age > 600:
                health = ProfileHealth.DEGRADED

        if profile.last_health_check_at:
            check_age = (datetime.now(UTC) - profile.last_health_check_at).total_seconds()
            if check_age > 3600:
                health = ProfileHealth.DEGRADED

        await db.execute(
            update(BrowserProfile)
            .where(BrowserProfile.id == profile_id)
            .values(last_health_check_at=datetime.now(UTC))
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
