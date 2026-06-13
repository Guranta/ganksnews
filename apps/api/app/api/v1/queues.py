from fastapi import APIRouter, Query

from app.core.redis import get_redis
from app.streams import StreamClient, ALL_STREAMS, DEAD_LETTER, stream_key
from app.streams.messages import StreamMessage, decode_data
from app.schemas.queues import QueueInfo, ConsumerGroupInfo, DeadLetterEntry

router = APIRouter()


@router.get("", response_model=list[QueueInfo])
async def list_queues():
    redis = await get_redis()
    client = StreamClient(redis)

    queues: list[QueueInfo] = []
    for name in ALL_STREAMS:
        key = stream_key(name)
        length = await client.length(name)

        groups_data = await client.groups_info(name)
        groups: list[ConsumerGroupInfo] = []
        for g in groups_data:
            groups.append(ConsumerGroupInfo(
                name=g.get("name", ""),
                pending=g.get("pending", 0),
                consumers=g.get("consumers", 0),
            ))

        queues.append(QueueInfo(stream=key, length=length, groups=groups))

    return queues


@router.get("/dead-letter", response_model=list[DeadLetterEntry])
async def list_dead_letter(count: int = Query(50, ge=1, le=200)):
    redis = await get_redis()
    client = StreamClient(redis)

    messages = await client.range(DEAD_LETTER, count=count)
    entries: list[DeadLetterEntry] = []
    for msg in messages:
        data = decode_data(msg.data)
        entries.append(DeadLetterEntry(
            id=msg.id,
            source_stream=data.get("source_stream", ""),
            original_id=data.get("original_id", ""),
            error=data.get("error", ""),
            original_data=data.get("original_data", {}),
            failed_at=data.get("failed_at", ""),
        ))
    return entries
