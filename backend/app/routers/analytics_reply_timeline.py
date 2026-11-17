from fastapi import APIRouter, Depends
from sqlalchemy import Integer, and_, case, cast, func, select
from sqlalchemy.orm import Session

from app.constants import MINIMUM_REPLY_SAMPLES_FOR_AVERAGE, ORDINARY_MESSAGE_TYPE
from app.db import get_db
from app.models import Chat, Message
from app.schemas.analytics import OwnerReplyTimelineStatistics, OwnerReplyTimelineYear
from app.routers.analytics_reply_timeline_queries import (
    build_reply_turns_statement,
)

router = APIRouter()


@router.get(
    "/owner-reply-timeline",
    response_model=OwnerReplyTimelineStatistics,
    summary="Get owner average reply time by year",
    description=(
        "Averages owner replies from message-turn transitions in personal chats "
        "across all imported accounts and platforms, grouped by the UTC calendar "
        "year of the owner reply. A reply is the first owner message after a "
        "contact-opened conversation session. Each session contributes at most "
        "one reply time, measured from the first contact message to the first "
        "owner message within 12 hours. Sessions without reliable direction or "
        "timestamps and sessions opened by the owner are excluded. Yearly "
        "averages are omitted when fewer than five replies are measured."
    ),
)
def get_owner_reply_timeline(
    db: Session = Depends(get_db),
) -> OwnerReplyTimelineStatistics:
    turns = build_reply_turns_statement(
        db,
        response_is_outgoing=True,
    ).subquery()
    dialect = db.get_bind().dialect.name
    year = (
        cast(func.strftime("%Y", turns.c.message_date), Integer)
        if dialect == "sqlite"
        else func.extract("year", func.timezone("UTC", turns.c.message_date))
    )
    history_year = (
        cast(func.strftime("%Y", Message.message_date), Integer)
        if dialect == "sqlite"
        else func.extract("year", func.timezone("UTC", Message.message_date))
    )
    history_bounds = db.execute(
        select(
            func.min(history_year).label("first_year"),
            func.max(history_year).label("last_year"),
        )
        .select_from(Message)
        .join(
            Chat,
            and_(
                Chat.id == Message.chat_id,
                Chat.platform == Message.platform,
                Chat.chat_type == "personal_chat",
            ),
        )
        .where(
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.message_date.is_not(None),
        )
    ).one()
    if history_bounds.first_year is None or history_bounds.last_year is None:
        return OwnerReplyTimelineStatistics(years=[])

    measured_reply_count = func.count(turns.c.elapsed_seconds)
    average_response_seconds = case(
        (
            measured_reply_count >= MINIMUM_REPLY_SAMPLES_FOR_AVERAGE,
            func.avg(turns.c.elapsed_seconds),
        ),
        else_=None,
    )
    if dialect == "sqlite":
        average_response_seconds = func.round(average_response_seconds, 3)
    rows = db.execute(
        select(
            year.label("year"),
            average_response_seconds.label("average_response_seconds"),
        )
        .select_from(turns)
        .group_by(year)
        .order_by(year)
    )
    averages_by_year = {
        int(row.year): float(row.average_response_seconds)
        for row in rows
        if row.average_response_seconds is not None
    }
    return OwnerReplyTimelineStatistics(
        years=[
            OwnerReplyTimelineYear(
                year=year_number,
                average_response_seconds=averages_by_year.get(year_number),
            )
            for year_number in range(
                int(history_bounds.first_year),
                int(history_bounds.last_year) + 1,
            )
        ]
    )
