from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CanonicalIdentity, Chat
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
        "the timeline to that identity in one-to-one personal chats; explicitly "
        "linked platform identities share one timeline. Pass chat_id to limit "
        "the timeline to one chat. Pass sender_id with chat_id to filter the "
        "timeline to one sender. Owner aliases are identified by "
        "platform-scoped stored user IDs. Contact "
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
    canonical_identity_id: Annotated[int | None, Query(gt=0)] = None,
    chat_id: Annotated[int | None, Query(gt=0)] = None,
    sender_id: Annotated[str | None, Query(min_length=1)] = None,
) -> CommunicationTimelineStatistics:
    if canonical_identity_id is not None and chat_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Select either a canonical identity or a chat, not both.",
        )
    if sender_id is not None and chat_id is None:
        raise HTTPException(
            status_code=400,
            detail="Select a chat when filtering the timeline by sender.",
        )
    if canonical_identity_id is not None:
        identity_id = db.scalar(
            select(CanonicalIdentity.id).where(
                CanonicalIdentity.id == canonical_identity_id,
            )
        )
        if identity_id is None:
            raise HTTPException(
                status_code=404,
                detail="Canonical identity not found.",
            )
    if chat_id is not None:
        selected_chat_id = db.scalar(select(Chat.id).where(Chat.id == chat_id))
        if selected_chat_id is None:
            raise HTTPException(status_code=404, detail="Chat not found.")
    return build_communication_timeline_statistics(
        db,
        canonical_identity_id=canonical_identity_id,
        chat_id=chat_id,
        sender_id=sender_id,
    )
