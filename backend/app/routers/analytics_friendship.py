from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, extract, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import ColumnElement

from app.constants import (
    ACTIVE_MINIMUM_TEXT_MESSAGES,
    ACTIVE_WINDOW_MONTHS,
    CLOSE_MINIMUM_ANNUAL_TEXT_MESSAGES,
    CLOSE_WINDOW_MONTHS,
    ORDINARY_MESSAGE_TYPE,
)
from app.db import get_db
from app.models import Account, CanonicalIdentity, Chat, Contact, Message
from app.schemas.analytics import (
    CloseFriendsTimelineStatistics,
    CloseFriendsTimelineYear,
)

router = APIRouter()

ContactGroupKey = tuple[object, ...]
FriendStatus = Literal["Active", "Close", "exClose"]

@dataclass
class YearlyContactActivity:
    text_message_count: int = 0
    owner_text_message_count: int = 0


@dataclass
class ContactActivity:
    yearly: dict[int, YearlyContactActivity] = field(default_factory=dict)
    recent_text_message_count: int = 0
    last_owner_message_at: datetime | None = None


@dataclass
class FriendshipAnalytics:
    statuses_by_contact: dict[ContactGroupKey, list[FriendStatus]]
    timeline: CloseFriendsTimelineStatistics


def contact_group_key(
    platform: str,
    account_id: int,
    contact_id: int | None,
    identity_id: int | None,
    identity_group_id: int | None,
    platform_user_id: str | None,
) -> ContactGroupKey:
    if identity_group_id is not None:
        return ("group", identity_group_id)
    if identity_id is not None:
        return ("identity", identity_id)
    if contact_id is not None:
        return ("contact", contact_id)
    return ("source", platform, account_id, platform_user_id)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _subtract_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 - months
    year, month_zero_indexed = divmod(month_index, 12)
    month = month_zero_indexed + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _utc_year_expression(dialect_name: str) -> ColumnElement[Any]:
    if dialect_name == "postgresql":
        return extract("year", func.timezone("UTC", Message.message_date))
    return extract("year", Message.message_date)


def _contact_key_from_activity_row(row: RowMapping) -> ContactGroupKey:
    key_kind = row["key_kind"]
    if key_kind == "source":
        return (
            "source",
            row["source_platform"],
            row["source_account_id"],
            row["source_platform_user_id"],
        )
    key_id = row["key_id"]
    return (key_kind, int(key_id)) if key_id is not None else (key_kind, None)


def _history_bounds(db: Session) -> tuple[datetime | None, datetime | None]:
    earliest, latest = db.execute(
        select(
            func.min(Message.message_date),
            func.max(Message.message_date),
        )
        .join(Chat, Chat.id == Message.chat_id)
        .where(
            Chat.platform == Message.platform,
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.message_date.is_not(None),
        )
    ).one()
    return (
        _as_utc(earliest) if earliest is not None else None,
        _as_utc(latest) if latest is not None else None,
    )


def _full_year_range(
    earliest: datetime | None,
    latest: datetime | None,
) -> tuple[list[int], int | None]:
    if earliest is None or latest is None:
        return [], None
    first_full_year = (
        earliest.year
        if earliest.date() == date(earliest.year, 1, 1)
        else earliest.year + 1
    )
    last_full_year = (
        latest.year
        if latest.date() == date(latest.year, 12, 31)
        else latest.year - 1
    )
    years = (
        list(range(first_full_year, last_full_year + 1))
        if first_full_year <= last_full_year
        else []
    )
    latest_partial_year = (
        latest.year
        if latest.date() != date(latest.year, 12, 31)
        else None
    )
    if latest_partial_year is not None and latest_partial_year <= earliest.year:
        latest_partial_year = None
    return years, latest_partial_year


def _close_through_year(
    activity: ContactActivity,
    qualifying_years: list[int],
    year: int,
) -> bool:
    for qualifying_year in qualifying_years:
        if qualifying_year > year:
            continue
        if all(
            activity.yearly.get(current_year, YearlyContactActivity())
            .owner_text_message_count
            > 0
            for current_year in range(qualifying_year, year + 1)
        ):
            return True
    return False


def build_friendship_analytics(
    db: Session,
    *,
    as_of: datetime | None = None,
) -> FriendshipAnalytics:
    current_time = _as_utc(as_of or datetime.now(timezone.utc))
    active_start = _subtract_months(current_time, ACTIVE_WINDOW_MONTHS)
    close_start = _subtract_months(current_time, CLOSE_WINDOW_MONTHS)

    owner_account = aliased(Account)
    owner_sender = (
        select(owner_account.id)
        .where(
            owner_account.platform == Message.platform,
            owner_account.platform_user_id == Message.sender_id,
        )
        .exists()
    )
    identity_group_id = CanonicalIdentity.identity_group_id
    identity_id = CanonicalIdentity.id
    contact_id = Contact.id
    key_kind = case(
        (identity_group_id.is_not(None), "group"),
        (identity_id.is_not(None), "identity"),
        (contact_id.is_not(None), "contact"),
        else_="source",
    )
    key_id = case(
        (identity_group_id.is_not(None), identity_group_id),
        (identity_id.is_not(None), identity_id),
        (contact_id.is_not(None), contact_id),
        else_=None,
    )
    source_key_condition = and_(
        identity_group_id.is_(None),
        identity_id.is_(None),
        contact_id.is_(None),
    )
    peer_pairs = (
        select(
            Chat.id.label("chat_id"),
            key_kind.label("key_kind"),
            key_id.label("key_id"),
            case(
                (source_key_condition, Chat.platform),
                else_=None,
            ).label("source_platform"),
            case(
                (source_key_condition, Chat.account_id),
                else_=None,
            ).label("source_account_id"),
            case(
                (source_key_condition, Message.sender_id),
                else_=None,
            ).label("source_platform_user_id"),
        )
        .select_from(Message)
        .join(Chat, Chat.id == Message.chat_id)
        .join(Account, Account.id == Chat.account_id)
        .outerjoin(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.platform == Chat.platform,
                or_(
                    Contact.id == Message.sender_contact_id,
                    and_(
                        Message.sender_contact_id.is_(None),
                        Message.sender_id.is_not(None),
                        Contact.platform_user_id == Message.sender_id,
                    ),
                ),
            ),
        )
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
        .where(
            Chat.platform == Account.platform,
            Message.platform == Chat.platform,
            Chat.chat_type == "personal_chat",
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.is_outgoing.is_(False),
            or_(
                Message.sender_id.is_not(None),
                Message.sender_contact_id.is_not(None),
            ),
            ~owner_sender,
        )
        .distinct()
        .cte("friendship_peer_pairs")
    )
    unambiguous_chats = (
        select(peer_pairs.c.chat_id)
        .group_by(peer_pairs.c.chat_id)
        .having(func.count() == 1)
        .cte("friendship_unambiguous_chats")
    )
    peers = (
        select(
            peer_pairs.c.chat_id,
            peer_pairs.c.key_kind,
            peer_pairs.c.key_id,
            peer_pairs.c.source_platform,
            peer_pairs.c.source_account_id,
            peer_pairs.c.source_platform_user_id,
        )
        .join(unambiguous_chats, unambiguous_chats.c.chat_id == peer_pairs.c.chat_id)
        .cte("friendship_peers")
    )
    year_expression = _utc_year_expression(db.get_bind().dialect.name)
    dated_text_message = and_(
        Message.message_date.is_not(None),
        Message.text_content.is_not(None),
        func.length(func.trim(Message.text_content)) > 0,
    )
    recent_text_message = and_(
        dated_text_message,
        Message.message_date >= active_start,
        Message.message_date <= current_time,
    )
    activity_rows = db.execute(
        select(
            peers.c.key_kind,
            peers.c.key_id,
            peers.c.source_platform,
            peers.c.source_account_id,
            peers.c.source_platform_user_id,
            year_expression.label("year"),
            func.count(Message.id).label("text_message_count"),
            func.sum(
                case((Message.is_outgoing.is_(True), 1), else_=0)
            ).label("owner_text_message_count"),
            func.sum(
                case((recent_text_message, 1), else_=0)
            ).label("recent_text_message_count"),
            func.max(
                case(
                    (
                        and_(
                            Message.is_outgoing.is_(True),
                            Message.message_date <= current_time,
                        ),
                        Message.message_date,
                    ),
                    else_=None,
                )
            ).label("last_owner_message_at"),
        )
        .select_from(peers)
        .join(Chat, Chat.id == peers.c.chat_id)
        .join(
            Message,
            and_(
                Message.chat_id == Chat.id,
                Message.platform == Chat.platform,
                Message.message_type == ORDINARY_MESSAGE_TYPE,
                Message.is_outgoing.in_((True, False)),
                dated_text_message,
            ),
        )
        .group_by(
            peers.c.key_kind,
            peers.c.key_id,
            peers.c.source_platform,
            peers.c.source_account_id,
            peers.c.source_platform_user_id,
            year_expression,
        )
    ).mappings().all()

    activity_by_contact: dict[ContactGroupKey, ContactActivity] = {}
    for row in activity_rows:
        key = _contact_key_from_activity_row(row)
        activity = activity_by_contact.setdefault(key, ContactActivity())
        year = int(row["year"])
        year_activity = activity.yearly.setdefault(year, YearlyContactActivity())
        text_message_count = int(row["text_message_count"] or 0)
        owner_message_count = int(row["owner_text_message_count"] or 0)
        year_activity.text_message_count += text_message_count
        year_activity.owner_text_message_count += owner_message_count
        activity.recent_text_message_count += int(
            row["recent_text_message_count"] or 0
        )
        if row["last_owner_message_at"] is not None:
            owner_message_at = _as_utc(row["last_owner_message_at"])
            if (
                activity.last_owner_message_at is None
                or owner_message_at > activity.last_owner_message_at
            ):
                activity.last_owner_message_at = owner_message_at

    earliest, latest = _history_bounds(db)
    full_years, latest_partial_year = _full_year_range(earliest, latest)
    close_counts = {year: 0 for year in full_years}
    statuses_by_contact: dict[ContactGroupKey, list[FriendStatus]] = {}

    for key, activity in activity_by_contact.items():
        qualifying_years = [
            year
            for year in full_years
            if (
                activity.yearly.get(year, YearlyContactActivity())
                .text_message_count
                >= CLOSE_MINIMUM_ANNUAL_TEXT_MESSAGES
                and activity.yearly.get(year, YearlyContactActivity())
                .owner_text_message_count
                > 0
            )
        ]
        for year in full_years:
            if _close_through_year(activity, qualifying_years, year):
                close_counts[year] += 1

        is_active = (
            activity.recent_text_message_count >= ACTIVE_MINIMUM_TEXT_MESSAGES
            and activity.last_owner_message_at is not None
            and activity.last_owner_message_at >= active_start
        )
        last_owner_message_at = activity.last_owner_message_at
        is_currently_close = (
            last_owner_message_at is not None
            and last_owner_message_at >= close_start
            and _close_through_year(
                activity,
                qualifying_years,
                last_owner_message_at.year,
            )
        )
        has_historical_close = bool(qualifying_years)
        statuses: list[FriendStatus] = []
        if is_active:
            statuses.append("Active")
        if is_currently_close:
            statuses.append("Close")
        elif has_historical_close:
            statuses.append("exClose")
        if statuses:
            statuses_by_contact[key] = statuses

    if latest_partial_year is not None and full_years:
        close_counts[latest_partial_year] = close_counts.get(
            latest_partial_year - 1,
            0,
        )
        output_years = [*full_years, latest_partial_year]
    else:
        output_years = full_years
    timeline = CloseFriendsTimelineStatistics(
        years=[
            CloseFriendsTimelineYear(
                year=year,
                close_friend_count=close_counts.get(year, 0),
            )
            for year in output_years
        ]
    )
    return FriendshipAnalytics(
        statuses_by_contact=statuses_by_contact,
        timeline=timeline,
    )


@router.get(
    "/close-friends-timeline",
    response_model=CloseFriendsTimelineStatistics,
    summary="Get close-friend counts by year",
    description=(
        "Counts personal-chat identities that reach 200 exchanged ordinary "
        "text-bearing messages in a complete UTC calendar year and remain "
        "close while the owner sends at least one text-bearing message each "
        "year. The incomplete first calendar year is excluded; an incomplete "
        "latest year repeats the preceding year's count. Explicitly linked "
        "identities are combined, and the result always spans all owner accounts."
    ),
)
def get_close_friends_timeline(
    db: Session = Depends(get_db),
) -> CloseFriendsTimelineStatistics:
    return build_friendship_analytics(db).timeline
