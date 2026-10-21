from fastapi import APIRouter

from .analytics_communication_balance import router as communication_balance_router
from .analytics_communication_timeline import router as communication_timeline_router
from .analytics_forgotten_contacts import router as forgotten_contacts_router
from .analytics_overview import (
    router as overview_router,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
router.include_router(overview_router)
router.include_router(communication_balance_router)
router.include_router(communication_timeline_router)
router.include_router(forgotten_contacts_router)
