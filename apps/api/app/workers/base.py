from __future__ import annotations

import asyncio
import logging
import signal
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.redis import get_redis
from app.streams import StreamClient, WEB_EVENTS, WORKER_EVENTS, EVT_HEARTBEAT, EVT_WORKER_STATUS, stream_key
from app.streams.messages import WorkerEventPayload, encode_payload
from app.workers.heartbeat import upsert_heartbeat

logger = logging.getLogger(__name__)


class WorkerBase:
    worker_type: str = "base"

    def __init__(self, worker_id: str | None = None):
        self.worker_id = worker_id or f"{self.worker_type}-{uuid.uuid4().hex[:8]}"
        self._running = False
        self._stream_client: StreamClient | None = None

    async def start(self) -> None:
        self._running = True
        redis = await get_redis()
        self._stream_client = StreamClient(redis)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_signal)

        logger.info("worker %s starting (id=%s)", self.worker_type, self.worker_id)
        await self._emit_event("started")
        await upsert_heartbeat(self.worker_type, self.worker_id, "running")

        try:
            await self.run()
        except asyncio.CancelledError:
            logger.info("worker %s cancelled", self.worker_id)
        except Exception as e:
            logger.error("worker %s crashed: %s", self.worker_id, e)
            await self._emit_event("error", detail={"error": str(e)})
            await upsert_heartbeat(self.worker_type, self.worker_id, "error", current_task=str(e))
        finally:
            await self._emit_event("stopped")
            await upsert_heartbeat(self.worker_type, self.worker_id, "stopped")
            self._running = False
            logger.info("worker %s stopped", self.worker_id)

    async def run(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def heartbeat(self, current_task: str | None = None) -> None:
        await upsert_heartbeat(self.worker_type, self.worker_id, "running", current_task=current_task)
        if self._stream_client:
            payload = WorkerEventPayload(
                worker_id=self.worker_id,
                worker_type=self.worker_type,
                event=EVT_HEARTBEAT,
            )
            await self._stream_client.xadd(WORKER_EVENTS, encode_payload(payload))

    async def _emit_event(self, event: str, detail: dict | None = None) -> None:
        if not self._stream_client:
            return
        payload = WorkerEventPayload(
            worker_id=self.worker_id,
            worker_type=self.worker_type,
            event=event,
            detail=detail,
        )
        await self._stream_client.xadd(WORKER_EVENTS, encode_payload(payload))

    def _handle_signal(self) -> None:
        logger.info("worker %s received signal, stopping", self.worker_id)
        self.stop()

    async def sleep(self, seconds: float) -> None:
        import asyncio
        await asyncio.sleep(seconds)
