from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import CrawlJob, CrawlJobStatus
from app.streams import CRAWL_JOBS, CG_LISTENER, WEB_EVENTS, RAW_TWEETS, EVT_CRAWL_JOB, EVT_TWEET_NEW
from app.streams.consumers import StreamConsumer
from app.streams.messages import encode_payload, WebEventPayload
from app.streams.client import StreamClient
from app.workers.base import WorkerBase
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class ListenerWorker(WorkerBase):
    worker_type = "listener"

    def __init__(self, worker_id: str | None = None):
        super().__init__(worker_id)
        self._consumer: StreamConsumer | None = None

    async def run(self) -> None:
        self._consumer = StreamConsumer(
            stream=CRAWL_JOBS,
            group=CG_LISTENER,
            consumer_name=self.worker_id,
        )

        await self._consumer.start(self._handle_message)

    async def _handle_message(self, msg) -> None:
        data = msg.data
        payload_str = data.get("payload", "{}")
        try:
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        except json.JSONDecodeError:
            payload = {}

        job_id = payload.get("job_id", "")
        target_username = payload.get("target_username", "unknown")

        await self.heartbeat(current_task=f"crawl:{target_username}")

        logger.info("listener processing job %s for @%s", job_id, target_username)

        if job_id:
            try:
                job_uuid = uuid.UUID(job_id)
            except ValueError:
                logger.error("invalid job_id: %s", job_id)
                return

            async with async_session_factory() as db:
                await db.execute(
                    update(CrawlJob)
                    .where(CrawlJob.id == job_uuid)
                    .values(status=CrawlJobStatus.running, started_at=datetime.now(timezone.utc))
                )
                await db.commit()

            await self._emit_web_event(EVT_CRAWL_JOB, {
                "job_id": job_id,
                "status": "running",
                "target_username": target_username,
            })

            try:
                tweets = await self._mock_crawl(target_username)

                for tweet in tweets:
                    redis = await self._get_redis()
                    client = StreamClient(redis)
                    tweet_data = {
                        "type": EVT_TWEET_NEW,
                        "payload": json.dumps(tweet),
                    }
                    await client.xadd(RAW_TWEETS, tweet_data)

                    await self._emit_web_event(EVT_TWEET_NEW, tweet)

                async with async_session_factory() as db:
                    await db.execute(
                        update(CrawlJob)
                        .where(CrawlJob.id == job_uuid)
                        .values(
                            status=CrawlJobStatus.completed,
                            completed_at=datetime.now(timezone.utc),
                        )
                    )
                    await db.commit()

                await self._emit_web_event(EVT_CRAWL_JOB, {
                    "job_id": job_id,
                    "status": "completed",
                    "target_username": target_username,
                    "tweets_found": len(tweets),
                })

                logger.info("listener completed job %s: %d tweets", job_id, len(tweets))

            except Exception as e:
                logger.error("listener job %s failed: %s", job_id, e)

                async with async_session_factory() as db:
                    await db.execute(
                        update(CrawlJob)
                        .where(CrawlJob.id == job_uuid)
                        .values(
                            status=CrawlJobStatus.failed,
                            completed_at=datetime.now(timezone.utc),
                            error_message=str(e),
                        )
                    )
                    await db.commit()

                await self._emit_web_event(EVT_CRAWL_JOB, {
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e),
                })

    async def _mock_crawl(self, username: str) -> list[dict]:
        return [
            {
                "tweet_id": f"mock_{username}_{i}",
                "author_username": username,
                "text": f"[Phase 2 mock tweet {i}] Hello from @{username}",
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(3)
        ]

    async def _emit_web_event(self, event_type: str, payload: dict) -> None:
        redis = await self._get_redis()
        client = StreamClient(redis)
        web_payload = WebEventPayload(type=event_type, payload=payload)
        await client.xadd(WEB_EVENTS, encode_payload(web_payload))

    async def _get_redis(self):
        from app.core.redis import get_redis
        return await get_redis()

    def stop(self) -> None:
        if self._consumer:
            self._consumer.stop()
        super().stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    worker = ListenerWorker()
    asyncio.run(worker.start())
