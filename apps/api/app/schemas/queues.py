from __future__ import annotations

from pydantic import BaseModel


class QueueInfo(BaseModel):
    stream: str
    length: int
    groups: list[ConsumerGroupInfo]


class ConsumerGroupInfo(BaseModel):
    name: str
    pending: int
    consumers: int


class DeadLetterEntry(BaseModel):
    id: str
    source_stream: str
    original_id: str
    error: str
    original_data: dict[str, str]
    failed_at: str
