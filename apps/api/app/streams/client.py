from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.core.config import settings
from app.streams.messages import StreamMessage, StreamPendingSummary

logger = logging.getLogger(__name__)


class StreamClient:
    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def xadd(self, stream: str, payload: dict[str, str], maxlen: int | None = None) -> str:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        effective_maxlen = maxlen or settings.STREAM_MAXLEN
        msg_id = await self._redis.xadd(key, payload, maxlen=effective_maxlen, approximate=True)
        return msg_id

    async def ensure_group(self, stream: str, group: str) -> None:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        try:
            await self._redis.xgroup_create(key, group, id="0", mkstream=True)
            logger.info("created consumer group %s on %s", group, key)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug("consumer group %s already exists on %s", group, key)
            else:
                raise

    async def read_group(
        self, stream: str, group: str, consumer: str, count: int | None = None, block_ms: int | None = None
    ) -> list[StreamMessage]:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        effective_count = count or settings.STREAM_CONSUMER_BATCH_SIZE
        effective_block = block_ms if block_ms is not None else settings.STREAM_CONSUMER_BLOCK_MS

        results = await self._redis.xreadgroup(
            group, consumer, {key: ">"}, count=effective_count, block=effective_block
        )

        messages: list[StreamMessage] = []
        if results:
            for stream_name, stream_messages in results:
                stream_key = stream_name if isinstance(stream_name, str) else stream_name.decode()
                for msg_id, data in stream_messages:
                    mid = msg_id if isinstance(msg_id, str) else msg_id.decode()
                    decoded_data = {k if isinstance(k, str) else k.decode(): v if isinstance(v, str) else v.decode() for k, v in data.items()}
                    messages.append(StreamMessage(id=mid, stream=stream_key, data=decoded_data))
        return messages

    async def ack(self, stream: str, group: str, message_id: str) -> None:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        await self._redis.xack(key, group, message_id)

    async def pending(self, stream: str, group: str) -> StreamPendingSummary:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        try:
            info = await self._redis.xpending_range(key, group, min="-", max="+", count=10)
            total_info = await self._redis.xpending(key, group)

            if total_info is None:
                return StreamPendingSummary()

            total = total_info.get("pending", 0) if isinstance(total_info, dict) else 0
            min_id = None
            max_id = None
            consumers: list[dict] = []

            if isinstance(total_info, dict):
                min_id = total_info.get("min")
                max_id = total_info.get("max")
                if isinstance(total_info.get("consumers"), list):
                    consumers = [
                        {"name": c if isinstance(c, str) else c.decode(), "pending": p}
                        for c, p in total_info["consumers"]
                    ]

            return StreamPendingSummary(total=total, min_id=min_id, max_id=max_id, consumers=consumers)
        except Exception as e:
            logger.warning("failed to get pending info for %s/%s: %s", key, group, e)
            return StreamPendingSummary()

    async def length(self, stream: str) -> int:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        return await self._redis.xlen(key)

    async def range(self, stream: str, count: int = 100, start: str = "-", end: str = "+") -> list[StreamMessage]:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        results = await self._redis.xrange(key, min=start, max=end, count=count)
        messages: list[StreamMessage] = []
        if results:
            for msg_id, data in results:
                mid = msg_id if isinstance(msg_id, str) else msg_id.decode()
                decoded_data = {k if isinstance(k, str) else k.decode(): v if isinstance(v, str) else v.decode() for k, v in data.items()}
                messages.append(StreamMessage(id=mid, stream=key, data=decoded_data))
        return messages

    async def range_latest(self, stream: str, count: int = 100) -> list[StreamMessage]:
        return await self.range(stream, count=count, start="-", end="+")

    async def stream_info(self, stream: str) -> dict:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        try:
            info = await self._redis.xinfo_stream(key)
            return info
        except Exception:
            return {}

    async def groups_info(self, stream: str) -> list[dict]:
        key = stream if ":" in stream else f"{settings.STREAM_PREFIX}:{stream}"
        try:
            return await self._redis.xinfo_groups(key)
        except Exception:
            return []
