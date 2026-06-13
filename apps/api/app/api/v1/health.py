from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version="0.1.0",
        database="unknown",
        redis="unknown",
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check():
    db_status = "ok"
    redis_status = "ok"

    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        redis = await get_redis()
        await redis.ping()
    except Exception:
        redis_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" and redis_status == "ok" else "degraded",
        version="0.1.0",
        database=db_status,
        redis=redis_status,
    )
