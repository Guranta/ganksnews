from __future__ import annotations

import asyncio
import json
import logging

from app.core.config import settings
from app.streams import CRAWL_JOBS, CG_DETAIL, RAW_TWEETS, EVT_TWEET_NEW
from app.streams.consumers import StreamConsumer
from app.workers.base import WorkerBase

logger = logging.getLogger(__name__)


class DetailWorker(WorkerBase):
    worker_type = "detail"

    def __init__(self, worker_id: str | None = None):
        super().__init__(worker_id)
        self._consumer: StreamConsumer | None = None

    async def run(self) -> None:
        self._consumer = StreamConsumer(
            stream=CRAWL_JOBS,
            group=CG_DETAIL,
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

        await self.heartbeat(current_task=f"detail:{target_username}")

        logger.info("detail worker processing job %s for @%s — placeholder, no real parsing yet", job_id, target_username)

    def stop(self) -> None:
        if self._consumer:
            self._consumer.stop()
        super().stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    worker = DetailWorker()
    asyncio.run(worker.start())
