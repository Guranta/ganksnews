from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import CrawlJob, CrawlJobStatus, TargetAccount, BrowserProfile
from app.streams import StreamClient, CRAWL_JOBS, WEB_EVENTS, EVT_CRAWL_JOB, stream_key
from app.streams.messages import encode_payload, WebEventPayload
from app.workers.base import WorkerBase
from sqlalchemy import select

logger = logging.getLogger(__name__)


class SchedulerWorker(WorkerBase):
    worker_type = "scheduler"

    def __init__(self, worker_id: str | None = None):
        super().__init__(worker_id)
        self._interval = settings.SCHEDULER_INTERVAL_SECONDS
        self._heartbeat_counter = 0

    async def run(self) -> None:
        logger.info("scheduler running with interval=%ds", self._interval)
        while self.running:
            try:
                await self._tick()
            except Exception as e:
                logger.error("scheduler tick error: %s", e)

            self._heartbeat_counter += 1
            if self._heartbeat_counter % 3 == 0:
                await self.heartbeat(current_task="idle")

            await asyncio.sleep(self._interval)

    async def _tick(self) -> None:
        async with async_session_factory() as db:
            result = await db.execute(
                select(TargetAccount).where(TargetAccount.status == "active")
            )
            targets = result.scalars().all()

            if not targets:
                logger.debug("scheduler tick: no active target accounts")
                return

            for target in targets:
                existing = await db.execute(
                    select(CrawlJob).where(
                        CrawlJob.target_account_id == target.id,
                        CrawlJob.status.in_([CrawlJobStatus.pending, CrawlJobStatus.running]),
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                profile_result = await db.execute(
                    select(BrowserProfile).where(
                        BrowserProfile.locked_by.is_(None),
                        BrowserProfile.status == "active",
                    ).limit(1)
                )
                profile = profile_result.scalar_one_or_none()

                job = CrawlJob(
                    job_type="timeline",
                    status=CrawlJobStatus.pending,
                    target_account_id=target.id,
                    browser_profile_id=profile.id if profile else None,
                )
                db.add(job)
                await db.flush()

                job_data = {
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "target_account_id": str(target.id),
                    "target_username": target.username,
                    "browser_profile_id": str(profile.id) if profile else "",
                    "status": job.status,
                }

                redis = await self._get_redis()
                client = StreamClient(redis)
                await client.xadd(CRAWL_JOBS, {"type": EVT_CRAWL_JOB, "payload": json.dumps(job_data)})

                web_payload = WebEventPayload(
                    type=EVT_CRAWL_JOB,
                    payload=job_data,
                )
                await client.xadd(WEB_EVENTS, encode_payload(web_payload))

                logger.info("scheduler created crawl job %s for @%s", job.id, target.username)

            await db.commit()

    async def _get_redis(self):
        from app.core.redis import get_redis
        return await get_redis()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    worker = SchedulerWorker()
    asyncio.run(worker.start())
