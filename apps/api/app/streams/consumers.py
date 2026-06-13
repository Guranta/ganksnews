from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable

from app.core.config import settings
from app.core.redis import get_redis
from app.streams.client import StreamClient
from app.streams.dead_letter import to_dead_letter
from app.streams.messages import StreamMessage

logger = logging.getLogger(__name__)


class StreamConsumer:
    def __init__(
        self,
        stream: str,
        group: str,
        consumer_name: str,
        count: int | None = None,
        block_ms: int | None = None,
        max_retries: int | None = None,
    ):
        self.stream = stream
        self.group = group
        self.consumer_name = consumer_name
        self.count = count or settings.STREAM_CONSUMER_BATCH_SIZE
        self.block_ms = block_ms if block_ms is not None else settings.STREAM_CONSUMER_BLOCK_MS
        self.max_retries = max_retries or settings.STREAM_MAX_RETRIES
        self._running = False
        self._client: StreamClient | None = None

    async def start(self, handler: Callable[[StreamMessage], Awaitable[None]]) -> None:
        self._running = True
        redis = await get_redis()
        self._client = StreamClient(redis)

        await self._client.ensure_group(self.stream, self.group)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_signal)

        logger.info("consumer %s started on %s/%s", self.consumer_name, self.stream, self.group)

        while self._running:
            try:
                messages = await self._client.read_group(
                    self.stream, self.group, self.consumer_name, count=self.count, block_ms=self.block_ms
                )

                for msg in messages:
                    await self._process_message(msg, handler)

            except asyncio.CancelledError:
                logger.info("consumer %s cancelled", self.consumer_name)
                break
            except Exception as e:
                logger.error("consumer %s error in read loop: %s", self.consumer_name, e)
                await asyncio.sleep(1)

        logger.info("consumer %s stopped", self.consumer_name)

    async def _process_message(self, msg: StreamMessage, handler: Callable[[StreamMessage], Awaitable[None]]) -> None:
        retry_count = 0
        try:
            retry_str = msg.data.get("_retry_count", "0")
            retry_count = int(retry_str) if isinstance(retry_str, str) else 0
        except (ValueError, TypeError):
            retry_count = 0

        try:
            await handler(msg)
            if self._client:
                await self._client.ack(self.stream, self.group, msg.id)
        except Exception as e:
            logger.error("handler failed for %s on %s: %s", msg.id, self.stream, e)
            retry_count += 1

            if retry_count >= self.max_retries:
                logger.warning("message %s exceeded max retries, sending to dead letter", msg.id)
                await to_dead_letter(self.stream, msg.id, msg.data, str(e))
                if self._client:
                    await self._client.ack(self.stream, self.group, msg.id)
            else:
                logger.info("message %s will be retried (attempt %d/%d)", msg.id, retry_count, self.max_retries)
                if self._client:
                    await self._client.ack(self.stream, self.group, msg.id)
                    new_data = {**msg.data, "_retry_count": str(retry_count)}
                    await self._client.xadd(self.stream, new_data)

    def stop(self) -> None:
        self._running = False

    def _handle_signal(self) -> None:
        logger.info("consumer %s received signal, stopping", self.consumer_name)
        self.stop()
