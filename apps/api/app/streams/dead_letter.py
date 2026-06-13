from __future__ import annotations

import logging

from app.core.redis import get_redis
from app.streams.client import StreamClient
from app.streams.messages import DeadLetterEntry, encode_payload
from app.streams import names

logger = logging.getLogger(__name__)


async def to_dead_letter(source_stream: str, message_id: str, data: dict[str, str], error: str) -> str:
    redis = await get_redis()
    client = StreamClient(redis)

    entry = DeadLetterEntry(
        source_stream=source_stream,
        original_id=message_id,
        error=error,
        original_data=data,
    )

    payload = encode_payload(entry)
    dl_id = await client.xadd(names.DEAD_LETTER, payload)
    logger.info("message %s from %s moved to dead letter as %s", message_id, source_stream, dl_id)
    return dl_id
