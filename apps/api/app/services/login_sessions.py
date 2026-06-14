import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import LoginSessionStatus
from app.repositories import login_sessions as repo
from app.schemas.login_sessions import LoginSessionCreate

logger = logging.getLogger(__name__)


class ConcurrentSessionLimitExceeded(Exception):
    pass


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _build_vnc_url(session_id: uuid.UUID, token: str) -> str:
    base = settings.NOVNC_PUBLIC_BASE_URL.rstrip("/")
    websocket_path = f"{base.lstrip('/')}/websockify"
    return f"{base}/vnc.html?path={websocket_path}&token={token}&autoconnect=true"


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
        running_count = await repo.count_by_status(db, LoginSessionStatus.RUNNING)
        if running_count >= settings.LOGIN_SESSION_MAX_CONCURRENT:
            raise ConcurrentSessionLimitExceeded(
                f"Already {running_count} running session(s), max {settings.LOGIN_SESSION_MAX_CONCURRENT}"
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

        vnc_url = _build_vnc_url(uuid.uuid4(), raw_token)

        create_kwargs = data.model_dump()
        create_kwargs["status"] = LoginSessionStatus.RUNNING
        create_kwargs["started_at"] = datetime.now(timezone.utc)
        create_kwargs["vnc_url"] = vnc_url
        create_kwargs["extra_data"] = extra_data

        session = await repo.create(db, **create_kwargs)

        session.vnc_url = _build_vnc_url(session.id, raw_token)

        await db.commit()

        logger.info(
            "Login session created id=%s status=running token_hash=%s...%s",
            session.id,
            token_hash[:8],
            token_hash[-4:],
        )
        return session


async def update_login_session_status(
    session_id: uuid.UUID,
    status: LoginSessionStatus,
    error_message: str | None = None,
):
    async with async_session_factory() as db:
        session = await repo.get_by_id(db, session_id)
        if session is None:
            return None

        extra_data = session.extra_data or {}
        if status in (LoginSessionStatus.COMPLETED, LoginSessionStatus.CANCELLED):
            extra_data.pop("novnc_token_hash", None)
            extra_data["novnc_revoked_at"] = datetime.now(timezone.utc).isoformat()

        session = await repo.update_status(
            db,
            session_id,
            status,
            error_message=error_message,
            extra_data=extra_data,
        )
        if session is None:
            return None
        await db.commit()
        return session


async def validate_novnc_token(token: str) -> bool:
    token_hash = _hash_token(token)
    async with async_session_factory() as db:
        sessions = await repo.find_running_with_token_hash(db)
        now = datetime.now(timezone.utc)
        for session in sessions:
            stored_hash = session.extra_data.get("novnc_token_hash", "")
            if stored_hash != token_hash:
                continue
            expires_str = session.extra_data.get("novnc_expires_at", "")
            try:
                expires_at = datetime.fromisoformat(expires_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            if now > expires_at:
                continue
            return True
    return False
