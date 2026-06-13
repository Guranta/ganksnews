import uuid

from fastapi import APIRouter, HTTPException, Query

from app.schemas.common import PaginatedResponse
from app.schemas.tweets import TweetResponse
from app.services import tweets as service

router = APIRouter()


@router.get("/latest", response_model=PaginatedResponse[TweetResponse])
async def list_latest_tweets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    author: str | None = None,
    search: str | None = None,
):
    items, total = await service.get_latest_tweets(page=page, page_size=page_size, author=author, search=search)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{tweet_id}", response_model=TweetResponse)
async def get_tweet(tweet_id: uuid.UUID):
    tweet = await service.get_tweet(tweet_id)
    if tweet is None:
        raise HTTPException(status_code=404, detail="Tweet not found")
    return tweet
