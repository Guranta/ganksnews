from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.target_accounts import router as target_accounts_router
from app.api.v1.monitoring_accounts import router as monitoring_accounts_router
from app.api.v1.browser_profiles import router as browser_profiles_router
from app.api.v1.monitor_lists import router as monitor_lists_router

router = APIRouter()

router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
router.include_router(target_accounts_router, prefix="/target-accounts", tags=["target-accounts"])
router.include_router(monitoring_accounts_router, prefix="/monitoring-accounts", tags=["monitoring-accounts"])
router.include_router(browser_profiles_router, prefix="/browser-profiles", tags=["browser-profiles"])
router.include_router(monitor_lists_router, prefix="/monitor-lists", tags=["monitor-lists"])
