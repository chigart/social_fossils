from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CanonicalIdentity
from app.schemas.analytics import CommunicationTimelineStatistics

from .analytics_communication_timeline_queries import (
    build_communication_timeline_statistics,
)

router = APIRouter()


@router.get(
    "/communication-timeline",
    response_model=CommunicationTimelineStatistics,
    summary="Get monthly communication activity",
    description=(
        "Returns ordinary-message counts in UTC calendar months across the "
        "combined imported owner history. Pass canonical_identity_id to limit "
        "the timeline to that Telegram identity in one-to-one personal chats. "
        "Owner aliases are identified by stored Telegram user IDs. Contact "
        "direction requires a non-owner sender with is_outgoing=false; when "
        "a selected canonical identity is requested, the sender must also "
        "match that identity's account-local contact mapping. Other direction "
        "is reported as unknown. Service events are excluded. Messages without "
        "timestamps are reported in the summary only and are not assigned to "
        "a month. Month rows between the earliest and latest dated ordinary "
        "messages are returned, including zero-activity months. Source account "
        "and contact identifiers identify the data provenance."
    ),
)
def get_communication_timeline(
    db: Session = Depends(get_db),
    canonical_identity_id: int | None = Query(default=None, gt=0),
) -> CommunicationTimelineStatistics:
    if canonical_identity_id is not None:
        identity_id = db.scalar(
            select(CanonicalIdentity.id).where(
                CanonicalIdentity.id == canonical_identity_id,
                CanonicalIdentity.platform == "telegram",
            )
        )
        if identity_id is None:
            raise HTTPException(
                status_code=404,
                detail="Telegram canonical identity not found.",
            )
    return build_communication_timeline_statistics(
        db,
        canonical_identity_id=canonical_identity_id,
    )
