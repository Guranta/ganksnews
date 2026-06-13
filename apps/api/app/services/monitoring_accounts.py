import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import BrowserProfileStatus, LoginSessionStatus, MonitoringAccountStatus
from app.repositories import browser_profiles as bp_repo
from app.repositories import login_sessions as ls_repo
from app.repositories import monitoring_accounts as repo
from app.schemas.monitoring_accounts import MonitoringAccountCreate, MonitoringAccountUpdate

logger = logging.getLogger(__name__)


class MonitoringAccountAlreadyExists(Exception):
    pass


def normalize_username(username: str) -> str:
    return username.strip().lstrip("@")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _build_vnc_url(session_id: uuid.UUID, token: str) -> str:
    base = settings.NOVNC_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/vnc.html?path={base}/websockify&token={token}&autoconnect=true"


async def get_monitoring_accounts(page: int = 1, page_size: int = 20):
    async with async_session_factory() as db:
        return await repo.list_all(db, page=page, page_size=page_size)


async def get_monitoring_account(account_id: uuid.UUID):
    async with async_session_factory() as db:
        return await repo.get_by_id(db, account_id)


async def create_monitoring_account(data: MonitoringAccountCreate):
    async with async_session_factory() as db:
        username = normalize_username(data.username)
        if not username:
            raise ValueError("Username is required")

        existing = await repo.get_by_username(db, platform="twitter", username=username)
        if existing:
            raise MonitoringAccountAlreadyExists(
                f"Monitoring account already exists for platform=twitter username={username}"
            )

        create_kwargs = data.model_dump()
        create_kwargs["username"] = username
        create_kwargs["platform"] = "twitter"
        create_kwargs["status"] = MonitoringAccountStatus.NEEDS_LOGIN

        try:
            account = await repo.create(db, **create_kwargs)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise MonitoringAccountAlreadyExists(
                f"Monitoring account already exists for platform=twitter username={username}"
            )

        logger.info("Monitoring account created id=%s username=%s status=needs_login", account.id, username)
        return account


async def create_monitoring_account_with_login_session(data: MonitoringAccountCreate):
    async with async_session_factory() as db:
        username = normalize_username(data.username)
        if not username:
            raise ValueError("Username is required")

        existing = await repo.get_by_username(db, platform="twitter", username=username)
        if existing:
            raise MonitoringAccountAlreadyExists(
                f"Monitoring account already exists for platform=twitter username={username}"
            )

        running_count = await ls_repo.count_by_status(db, LoginSessionStatus.RUNNING)
        if running_count >= settings.LOGIN_SESSION_MAX_CONCURRENT:
            raise ValueError(
                f"Already {running_count} running session(s), max {settings.LOGIN_SESSION_MAX_CONCURRENT}"
            )

        account_kwargs = data.model_dump()
        account_kwargs["username"] = username
        account_kwargs["platform"] = "twitter"
        account_kwargs["status"] = MonitoringAccountStatus.NEEDS_LOGIN

        try:
            account = await repo.create(db, **account_kwargs)
        except IntegrityError:
            await db.rollback()
            raise MonitoringAccountAlreadyExists(
                f"Monitoring account already exists for platform=twitter username={username}"
            )

        profile = await bp_repo.create(
            db,
            name=f"twitter:@{username}",
            profile_path=f"{settings.BROWSER_PROFILES_DIR}/twitter/{account.id}",
            monitoring_account_id=account.id,
            status=BrowserProfileStatus.IN_USE,
            provider=settings.BROWSER_PROVIDER,
        )

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.LOGIN_SESSION_TOKEN_TTL_SECONDS
        )
        extra_data = {
            "novnc_token_hash": token_hash,
            "novnc_expires_at": expires_at.isoformat(),
        }

        login_session = await ls_repo.create(
            db,
            browser_profile_id=profile.id,
            monitoring_account_id=account.id,
            status=LoginSessionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            vnc_url=_build_vnc_url(uuid.uuid4(), raw_token),
            extra_data=extra_data,
        )

        login_session.vnc_url = _build_vnc_url(login_session.id, raw_token)

        await db.commit()

        logger.info(
            "Onboarding created account=%s profile=%s session=%s username=%s",
            account.id,
            profile.id,
            login_session.id,
            username,
        )

        return account, profile, login_session, login_session.vnc_url


async def update_monitoring_account(account_id: uuid.UUID, data: MonitoringAccountUpdate):
    async with async_session_factory() as db:
        account = await repo.get_by_id(db, account_id)
        if account is None:
            return None
        account = await repo.update(db, account, **data.model_dump(exclude_unset=True))
        await db.commit()
        return account


async def delete_monitoring_account(account_id: uuid.UUID):
    async with async_session_factory() as db:
        account = await repo.get_by_id(db, account_id)
        if account is None:
            return False
        await repo.delete(db, account)
        await db.commit()
        return True
