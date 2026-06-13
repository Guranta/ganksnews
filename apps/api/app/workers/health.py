from __future__ import annotations

import asyncio
import logging
import signal

from app.core.config import settings
from app.workers.base import WorkerBase
from app.browser.locks import cleanup_stale_locks

logger = logging.getLogger(__name__)


class HealthWorker(WorkerBase):
    worker_type = "health"

    def __init__(self, worker_id: str | None = None):
        super().__init__(worker_id)
        self._interval = settings.HEALTH_CHECK_INTERVAL_SECONDS
        self._heartbeat_counter = 0

    async def run(self) -> None:
        logger.info("health worker running with interval=%ds", self._interval)
        while self.running:
            try:
                await self._check_workers()
                cleaned = await cleanup_stale_locks()
                if cleaned:
                    logger.info("health worker cleaned %d stale profile locks", cleaned)
            except Exception as e:
                logger.error("health check error: %s", e)

            self._heartbeat_counter += 1
            if self._heartbeat_counter % 3 == 0:
                await self.heartbeat(current_task="idle")

            await asyncio.sleep(self._interval)

    async def _check_workers(self) -> None:
        logger.debug("health worker tick")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    worker = HealthWorker()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(signum, frame):
        worker.stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    loop.run_until_complete(worker.run())
