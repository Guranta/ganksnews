from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.redis import get_redis
from app.streams import StreamClient, WEB_EVENTS, EVT_TEST, stream_key
from app.streams.messages import WebEventPayload, encode_payload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stream")
async def event_stream(request: Request):
    async def generate():
        redis = await get_redis()
        client = StreamClient(redis)
        last_id = "$"

        while True:
            if await request.is_disconnected():
                break

            try:
                messages = await client.range_latest(WEB_EVENTS, count=1)
                if messages:
                    last_id = messages[-1].id

                new_messages = await redis.xread(
                    {stream_key(WEB_EVENTS): last_id},
                    count=10,
                    block=settings.STREAM_CONSUMER_BLOCK_MS,
                )

                if new_messages:
                    for _stream_name, stream_messages in new_messages:
                        for msg_id, msg_data in stream_messages:
                            last_id = msg_id
                            event_type = msg_data.get("type", "unknown")
                            payload_str = msg_data.get("payload", "{}")
                            try:
                                payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                            except json.JSONDecodeError:
                                payload = payload_str
                            data = json.dumps({"id": msg_id, "type": event_type, "payload": payload})
                            yield f"event: {event_type}\ndata: {data}\n\n"
                else:
                    yield f": heartbeat {datetime.now(timezone.utc).isoformat()}\n\n"

            except Exception as e:
                logger.error("SSE stream error: %s", e)
                yield f": error {str(e)}\n\n"
                await asyncio.sleep(1)

            await asyncio.sleep(0.1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/recent")
async def recent_events(count: int = Query(20, ge=1, le=200)):
    redis = await get_redis()
    client = StreamClient(redis)

    messages = await client.range(WEB_EVENTS, count=count)
    events = []
    for msg in messages:
        data = msg.data
        payload_str = data.get("payload", "{}")
        try:
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        except json.JSONDecodeError:
            payload = payload_str
        events.append({
            "id": msg.id,
            "type": data.get("type", "unknown"),
            "payload": payload,
            "ts": data.get("ts", ""),
        })
    events.reverse()
    return events


@router.post("/test")
async def emit_test_event(message: str = "test event"):
    redis = await get_redis()
    client = StreamClient(redis)

    payload = WebEventPayload(
        type=EVT_TEST,
        payload={"message": message, "emitted_at": datetime.now(timezone.utc).isoformat()},
    )
    msg_id = await client.xadd(WEB_EVENTS, encode_payload(payload))
    return {"ok": True, "stream_id": msg_id}
