from __future__ import annotations

import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class StreamMessage(BaseModel):
    id: str
    stream: str
    data: dict[str, str]


class WebEventPayload(BaseModel):
    type: str
    payload: dict = Field(default_factory=dict)
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkerEventPayload(BaseModel):
    worker_id: str
    worker_type: str
    event: str
    detail: dict | None = None


class DeadLetterEntry(BaseModel):
    source_stream: str
    original_id: str
    error: str
    original_data: dict[str, str]
    failed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StreamPendingSummary(BaseModel):
    total: int = 0
    min_id: str | None = None
    max_id: str | None = None
    consumers: list[dict] = Field(default_factory=list)


def encode_payload(payload: BaseModel) -> dict[str, str]:
    return {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in payload.model_dump().items() if v is not None}


def decode_data(data: dict[str, str]) -> dict:
    result: dict[str, str | dict | list] = {}
    for k, v in data.items():
        try:
            result[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            result[k] = v
    return result
