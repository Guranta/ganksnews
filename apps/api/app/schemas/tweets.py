from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class TweetResponse(BaseModel):
    id: uuid.UUID
    platform: str
    tweet_id: str
    author_username: str
    author_display_name: str | None
    text: str | None
    url: str | None
    posted_at: datetime | None
    like_count: int | None
    retweet_count: int | None
    reply_count: int | None
    quote_count: int | None
    view_count: int | None
    is_retweet: bool
    is_quote: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
