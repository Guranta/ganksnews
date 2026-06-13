from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BrowserProfile, MonitoringAccount, TargetAccount, TargetAccountStatus, Tweet, WorkerHeartbeat


async def get_summary(db: AsyncSession) -> dict:
    target_count = (
        await db.execute(select(func.count()).select_from(TargetAccount).where(TargetAccount.status == TargetAccountStatus.ACTIVE))
    ).scalar_one()

    monitoring_count = (await db.execute(select(func.count()).select_from(MonitoringAccount))).scalar_one()

    browser_count = (await db.execute(select(func.count()).select_from(BrowserProfile))).scalar_one()

    tweet_count = (await db.execute(select(func.count()).select_from(Tweet))).scalar_one()

    worker_count = (await db.execute(select(func.count()).select_from(WorkerHeartbeat))).scalar_one()

    return {
        "active_target_accounts": target_count,
        "monitoring_accounts": monitoring_count,
        "browser_profiles": browser_count,
        "total_tweets": tweet_count,
        "workers_online": worker_count,
    }
