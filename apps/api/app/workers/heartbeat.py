from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import WorkerHeartbeat


async def upsert_heartbeat(
    worker_type: str,
    worker_id: str,
    status: str = "running",
    current_task: str | None = None,
    metadata: dict | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    async with async_session_factory() as db:
        stmt = insert(WorkerHeartbeat).values(
            worker_type=worker_type,
            worker_id=worker_id,
            status=status,
            current_task=current_task,
            metadata_=metadata,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="worker_heartbeats_worker_type_worker_id_key",
            set_={
                "status": stmt.excluded.status,
                "current_task": stmt.excluded.current_task,
                "metadata_": metadata,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await db.execute(stmt)
        await db.commit()


async def get_active_workers(offline_after_seconds: int | None = None) -> list[WorkerHeartbeat]:
    from sqlalchemy import select

    threshold = offline_after_seconds or settings.WORKER_OFFLINE_AFTER_SECONDS
    cutoff = datetime.now(timezone.utc).timestamp() - threshold

    async with async_session_factory() as db:
        result = await db.execute(
            select(WorkerHeartbeat).order_by(WorkerHeartbeat.worker_type, WorkerHeartbeat.worker_id)
        )
        workers = result.scalars().all()

    active = []
    for w in workers:
        if w.status in ("running",) and w.updated_at and w.updated_at.timestamp() >= cutoff:
            active.append(w)
        elif w.status not in ("stopped",):
            active.append(w)
    return active


async def get_all_workers() -> list[WorkerHeartbeat]:
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(WorkerHeartbeat).order_by(WorkerHeartbeat.worker_type, WorkerHeartbeat.worker_id)
        )
        return result.scalars().all()
