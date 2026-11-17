from fastapi import APIRouter

from .analytics_chat_insights import router as chat_insights_router
from .analytics_contacts import router as contacts_router
from .analytics_communication_balance import router as communication_balance_router
from .analytics_communication_timeline import router as communication_timeline_router
from .analytics_forgotten_contacts import router as forgotten_contacts_router
from .analytics_friendship import router as friendship_router
from .analytics_overview import (
    router as overview_router,
)
from .analytics_reply_timeline import router as reply_timeline_router

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
router.include_router(overview_router)
router.include_router(contacts_router)
router.include_router(chat_insights_router)
router.include_router(communication_balance_router)
router.include_router(communication_timeline_router)
router.include_router(forgotten_contacts_router)
router.include_router(friendship_router)
router.include_router(reply_timeline_router)
