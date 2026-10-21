from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Chat, Contact, Message, TelegramAccount
from app.schemas.analytics import (
    ChatStatistics,
    CommunicationBalanceClassification,
    CommunicationBalanceContact,
    CommunicationBalanceStatistics,
    CommunicationBalanceSummary,
    ContactStatistics,
    ForgottenContact,
    ForgottenContactEvidenceStatus,
    ForgottenContactMonthlyActivity,
    ForgottenContactsStatistics,
    ForgottenContactsSummary,
    OverviewStatistics,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

ORDINARY_MESSAGE_TYPE = "message"
SERVICE_MESSAGE_TYPE = "service"
MINIMUM_BALANCE_TEXT_LENGTH = 500
BALANCED_OWNER_SHARE_MINIMUM = 0.40
BALANCED_OWNER_SHARE_MAXIMUM = 0.60
STRONG_OWNER_SHARE_MINIMUM = 0.80
STRONG_CONTACT_OWNER_SHARE_MAXIMUM = 0.20
FORGOTTEN_RECENT_WINDOW_DAYS = 90
FORGOTTEN_INACTIVE_DAYS = 90
FORGOTTEN_MIN_HISTORICAL_MESSAGES = 20
FORGOTTEN_MIN_HISTORICAL_ACTIVE_DAYS = 5
FORGOTTEN_MIN_HISTORICAL_ACTIVE_MONTHS = 3
FORGOTTEN_MIN_BASELINE_SPAN_DAYS = 90
FORGOTTEN_DECLINE_THRESHOLD = 0.50
FORGOTTEN_RECENT_MONTH_DAYS = 30
FORGOTTEN_EVIDENCE_MESSAGE_CAP = 100
FORGOTTEN_SCORE_INACTIVITY_CAP_DAYS = 180
FORGOTTEN_SCORE_INACTIVITY_WEIGHT = 0.60
FORGOTTEN_SCORE_DECLINE_WEIGHT = 0.40
FORGOTTEN_MAX_LIMIT = 500


def classify_communication_balance(
    owner_text_share: float | None,
    total_text_length: int,
) -> CommunicationBalanceClassification:
    if total_text_length < MINIMUM_BALANCE_TEXT_LENGTH or owner_text_share is None:
        return "insufficient_data"
    if owner_text_share >= STRONG_OWNER_SHARE_MINIMUM:
        return "strongly_owner"
    if owner_text_share <= STRONG_CONTACT_OWNER_SHARE_MAXIMUM:
        return "strongly_contact"
    if BALANCED_OWNER_SHARE_MINIMUM <= owner_text_share <= BALANCED_OWNER_SHARE_MAXIMUM:
        return "balanced"
    if owner_text_share > BALANCED_OWNER_SHARE_MAXIMUM:
        return "mostly_owner"
    return "mostly_contact"


@router.get(
    "/overview",
    response_model=OverviewStatistics,
    summary="Get communication overview",
    description=(
        "Counts all account, chat, and message rows. Ordinary messages are rows "
        "with message_type='message'; service events are rows with "
        "message_type='service'. Other stored types contribute only to total "
        "messages. Timestamp bounds ignore messages with a null date."
    ),
)
def get_overview(db: Session = Depends(get_db)) -> OverviewStatistics:
    result = db.execute(
        select(
            select(func.count(TelegramAccount.id)).scalar_subquery().label("total_imported_accounts"),
            select(func.count(Chat.id)).scalar_subquery().label("total_chats"),
            func.count(Message.id).label("total_messages"),
            func.count(
                case((Message.message_type == ORDINARY_MESSAGE_TYPE, Message.id))
            ).label("total_ordinary_messages"),
            func.count(
                case((Message.message_type == SERVICE_MESSAGE_TYPE, Message.id))
            ).label("total_service_messages"),
            func.min(Message.message_date).label("earliest_message_timestamp"),
            func.max(Message.message_date).label("latest_message_timestamp"),
        ).select_from(Message)
    ).one()

    return OverviewStatistics(**result._mapping)


@router.get(
    "/chats",
    response_model=list[ChatStatistics],
    summary="Get communication statistics by chat",
    description=(
        "Returns every chat, including chats with no messages. Counts include "
        "all stored message types; ordinary and service counts use the exact "
        "'message' and 'service' values. Distinct senders count non-null "
        "sender Telegram IDs as normalized and stored by the importer."
    ),
)
def get_chat_statistics(db: Session = Depends(get_db)) -> list[ChatStatistics]:
    statement = (
        select(
            Chat.id.label("chat_id"),
            Chat.telegram_chat_id,
            Chat.title,
            Chat.chat_type,
            func.count(Message.id).label("total_messages"),
            func.count(
                case((Message.message_type == ORDINARY_MESSAGE_TYPE, Message.id))
            ).label("ordinary_messages"),
            func.count(
                case((Message.message_type == SERVICE_MESSAGE_TYPE, Message.id))
            ).label("service_messages"),
            func.min(Message.message_date).label("earliest_message_timestamp"),
            func.max(Message.message_date).label("latest_message_timestamp"),
            func.count(func.distinct(Message.sender_telegram_id)).label(
                "distinct_identified_senders"
            ),
        )
        .select_from(Chat)
        .outerjoin(Message, Message.chat_id == Chat.id)
        .group_by(Chat.id, Chat.telegram_chat_id, Chat.title, Chat.chat_type)
        .order_by(Chat.id)
    )
    return [ChatStatistics(**row._mapping) for row in db.execute(statement)]


@router.get(
    "/contacts",
    response_model=list[ContactStatistics],
    summary="Get communication statistics by sender/contact",
    description=(
        "Groups incoming messages by account-local Telegram user ID and links "
        "a contact only by that ID, never by display name. Sender IDs without "
        "a matching contact remain in separate unlinked groups; null sender "
        "IDs form an unknown-sender group per account. Messages marked "
        "outgoing, and messages whose sender ID matches the account owner, "
        "are excluded. Counts include all message types, with ordinary and "
        "service counts reported separately."
    ),
)
def get_contact_statistics(db: Session = Depends(get_db)) -> list[ContactStatistics]:
    statement = (
        select(
            Chat.account_id.label("account_id"),
            Contact.id.label("contact_id"),
            Message.sender_telegram_id.label("telegram_user_id"),
            Contact.display_name.label("display_name"),
            func.count(Message.id).label("total_messages_sent"),
            func.count(
                case((Message.message_type == ORDINARY_MESSAGE_TYPE, Message.id))
            ).label("ordinary_messages_sent"),
            func.count(
                case((Message.message_type == SERVICE_MESSAGE_TYPE, Message.id))
            ).label("service_events_attributed"),
        )
        .select_from(Message)
        .join(Chat, Message.chat_id == Chat.id)
        .join(TelegramAccount, Chat.account_id == TelegramAccount.id)
        .outerjoin(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.telegram_user_id == Message.sender_telegram_id,
            ),
        )
        .where(
            Message.is_outgoing.is_not(True),
            or_(
                Message.sender_telegram_id.is_(None),
                TelegramAccount.telegram_user_id.is_(None),
                Message.sender_telegram_id != TelegramAccount.telegram_user_id,
            ),
        )
        .group_by(
            Chat.account_id,
            Contact.id,
            Message.sender_telegram_id,
            Contact.display_name,
        )
        .order_by(Chat.account_id, Contact.display_name, Message.sender_telegram_id)
    )
    return [ContactStatistics(**row._mapping) for row in db.execute(statement)]


@router.get(
    "/communication-balance",
    response_model=CommunicationBalanceStatistics,
    summary="Get communication balance by contact",
    description=(
        "Compares normalized text volume in eligible one-to-one Telegram "
        "personal chats. Text length is the number of Unicode code points "
        "in stored text_content (PostgreSQL character length): spaces, "
        "punctuation, and emoji code points count; UTF-8 bytes, metadata, "
        "service events, empty text, and media-only content do not. "
        "A message containing text and media contributes only its text. "
        "The initial heuristics mark fewer than 500 total text characters "
        "insufficient, owner shares from 40% through 60% balanced, above "
        "60% and below 80% mostly_owner, and below 40% and above 20% "
        "mostly_contact; owner shares at or above 80% are strongly_owner "
        "and at or below 20% are strongly_contact. "
        "These descriptive thresholds are not scientifically validated. Chats are included "
        "only when chat_type is 'personal_chat', the account owner ID is "
        "known, and exactly one non-owner sender ID in ordinary messages "
        "resolves to a contact; "
        "group chats and ambiguous records are excluded. Only ordinary "
        "messages with consistent sender ID and is_outgoing values affect "
        "text volume and included message counts."
    ),
)
def get_communication_balance(
    db: Session = Depends(get_db),
    sort_by: Literal["display_name", "owner_share", "message_count"] = Query(
        default="display_name",
        description="Sort by display name, owner text share ascending, or known-direction message count descending.",
    ),
) -> CommunicationBalanceStatistics:
    peers = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Message.sender_telegram_id.label("peer_telegram_user_id"),
        )
        .join(Message, Message.chat_id == Chat.id)
        .join(TelegramAccount, TelegramAccount.id == Chat.account_id)
        .where(
            Chat.chat_type == "personal_chat",
            TelegramAccount.telegram_user_id.is_not(None),
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.sender_telegram_id.is_not(None),
            Message.sender_telegram_id != TelegramAccount.telegram_user_id,
        )
        .distinct()
        .cte("private_chat_peers")
    )
    single_peer_chats = (
        select(peers.c.chat_id)
        .group_by(peers.c.chat_id)
        .having(func.count() == 1)
        .cte("single_peer_chats")
    )
    eligible_pairs = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Contact.id.label("contact_id"),
            Contact.telegram_user_id.label("contact_telegram_user_id"),
            TelegramAccount.telegram_user_id.label("owner_telegram_user_id"),
            Contact.display_name.label("display_name"),
        )
        .join(TelegramAccount, TelegramAccount.id == Chat.account_id)
        .join(peers, peers.c.chat_id == Chat.id)
        .join(single_peer_chats, single_peer_chats.c.chat_id == Chat.id)
        .join(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.telegram_user_id == peers.c.peer_telegram_user_id,
            ),
        )
        .cte("eligible_private_chat_pairs")
    )

    is_ordinary = Message.message_type == ORDINARY_MESSAGE_TYPE
    owner_direction = and_(
        Message.sender_telegram_id == eligible_pairs.c.owner_telegram_user_id,
        Message.is_outgoing.is_(True),
    )
    contact_direction = and_(
        Message.sender_telegram_id == eligible_pairs.c.contact_telegram_user_id,
        Message.is_outgoing.is_(False),
    )
    known_direction = or_(owner_direction, contact_direction)
    text_length = func.length(func.coalesce(Message.text_content, ""))
    if db.get_bind().dialect.name == "postgresql":
        utc_message_date = func.date(func.timezone("UTC", Message.message_date))
    else:
        utc_message_date = func.date(Message.message_date)

    statement = (
        select(
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            eligible_pairs.c.contact_telegram_user_id.label("telegram_user_id"),
            eligible_pairs.c.display_name,
            func.coalesce(
                func.sum(
                    case(
                        (and_(is_ordinary, owner_direction), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("owner_message_count"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(is_ordinary, contact_direction), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("contact_message_count"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(is_ordinary, owner_direction),
                            text_length,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("owner_text_length"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(is_ordinary, contact_direction),
                            text_length,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("contact_text_length"),
            func.count(
                case(
                    (and_(is_ordinary, known_direction), Message.id),
                )
            ).label("known_ordinary_message_count"),
            func.count(
                case((is_ordinary, Message.id))
            ).label("ordinary_message_count"),
            func.min(
                case(
                    (and_(is_ordinary, known_direction), Message.message_date),
                )
            ).label("first_message_at"),
            func.max(
                case(
                    (and_(is_ordinary, known_direction), Message.message_date),
                )
            ).label("last_message_at"),
            func.count(
                func.distinct(
                    case(
                        (
                            and_(
                                is_ordinary,
                                known_direction,
                                Message.message_date.is_not(None),
                            ),
                            utc_message_date,
                        )
                    )
                )
            ).label("distinct_active_days"),
        )
        .select_from(eligible_pairs)
        .join(Message, Message.chat_id == eligible_pairs.c.chat_id)
        .group_by(
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            eligible_pairs.c.contact_telegram_user_id,
            eligible_pairs.c.display_name,
        )
        .having(func.count(case((is_ordinary, Message.id))) > 0)
    )

    contacts: list[CommunicationBalanceContact] = []
    for row in db.execute(statement):
        owner_text_length = int(row.owner_text_length)
        contact_text_length = int(row.contact_text_length)
        total_text_length = owner_text_length + contact_text_length
        owner_share = (
            owner_text_length / total_text_length if total_text_length else None
        )
        contact_share = (
            contact_text_length / total_text_length if total_text_length else None
        )
        owner_message_count = int(row.owner_message_count)
        contact_message_count = int(row.contact_message_count)
        contacts.append(
            CommunicationBalanceContact(
                account_id=row.account_id,
                contact_id=row.contact_id,
                telegram_user_id=row.telegram_user_id,
                display_name=row.display_name,
                owner_message_count=owner_message_count,
                contact_message_count=contact_message_count,
                total_message_count=owner_message_count + contact_message_count,
                excluded_unknown_direction_message_count=(
                    int(row.ordinary_message_count)
                    - int(row.known_ordinary_message_count)
                ),
                owner_text_length=owner_text_length,
                contact_text_length=contact_text_length,
                total_text_length=total_text_length,
                owner_text_share=owner_share,
                contact_text_share=contact_share,
                absolute_share_difference=(
                    abs(owner_share - contact_share)
                    if owner_share is not None and contact_share is not None
                    else None
                ),
                owner_share_percentage=(
                    owner_share * 100 if owner_share is not None else None
                ),
                contact_share_percentage=(
                    contact_share * 100 if contact_share is not None else None
                ),
                classification=classify_communication_balance(
                    owner_share,
                    total_text_length,
                ),
                first_message_at=row.first_message_at,
                last_message_at=row.last_message_at,
                distinct_active_days=int(row.distinct_active_days),
            )
        )

    if sort_by == "owner_share":
        contacts.sort(
            key=lambda contact: (
                contact.owner_text_share is None,
                contact.owner_text_share or 0.0,
                contact.contact_id,
            )
        )
    elif sort_by == "message_count":
        contacts.sort(
            key=lambda contact: (-contact.total_message_count, contact.contact_id)
        )
    else:
        contacts.sort(
            key=lambda contact: (
                (contact.display_name or "").casefold(),
                contact.contact_id,
            )
        )

    summary = CommunicationBalanceSummary(
        eligible_contacts=len(contacts),
        balanced_contacts=sum(c.classification == "balanced" for c in contacts),
        mostly_owner_contacts=sum(c.classification == "mostly_owner" for c in contacts),
        mostly_contact_contacts=sum(
            c.classification == "mostly_contact" for c in contacts
        ),
        strongly_owner_contacts=sum(
            c.classification == "strongly_owner" for c in contacts
        ),
        strongly_contact_contacts=sum(
            c.classification == "strongly_contact" for c in contacts
        ),
        insufficient_data_contacts=sum(
            c.classification == "insufficient_data" for c in contacts
        ),
        owner_text_length=sum(c.owner_text_length for c in contacts),
        contact_text_length=sum(c.contact_text_length for c in contacts),
        total_text_length=sum(c.total_text_length for c in contacts),
        owner_message_count=sum(c.owner_message_count for c in contacts),
        contact_message_count=sum(c.contact_message_count for c in contacts),
        total_message_count=sum(c.total_message_count for c in contacts),
        excluded_unknown_direction_message_count=sum(
            c.excluded_unknown_direction_message_count for c in contacts
        ),
    )
    return CommunicationBalanceStatistics(summary=summary, contacts=contacts)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utc_month_expression(db: Session):
    if db.get_bind().dialect.name == "postgresql":
        return func.to_char(
            func.timezone("UTC", Message.message_date),
            "YYYY-MM",
        )
    return func.strftime("%Y-%m", Message.message_date)


def build_forgotten_contacts_statistics(
    db: Session,
    *,
    account_id: int | None = None,
    sort_by: Literal[
        "ranking_score",
        "display_name",
        "days_since_last_communication",
        "historical_message_count",
    ] = "ranking_score",
    limit: int = 100,
    as_of: datetime | None = None,
) -> ForgottenContactsStatistics:
    if not 1 <= limit <= FORGOTTEN_MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {FORGOTTEN_MAX_LIMIT}.")

    account_count_statement = select(func.count(TelegramAccount.id))
    if account_id is not None:
        account_count_statement = account_count_statement.where(
            TelegramAccount.id == account_id
        )
    matching_account_count = int(db.scalar(account_count_statement) or 0)
    if account_id is not None and matching_account_count == 0:
        raise HTTPException(status_code=404, detail="Telegram account not found.")
    if account_id is None and matching_account_count > 1:
        raise HTTPException(
            status_code=400,
            detail="Specify account_id when more than one Telegram account exists.",
        )
    if account_id is None and matching_account_count == 1:
        account_id = db.scalar(select(TelegramAccount.id))
    if matching_account_count == 0:
        return ForgottenContactsStatistics(
            summary=ForgottenContactsSummary(
                account_id=None,
                eligible_contacts=0,
                meaningful_historical_contacts=0,
                currently_inactive_contacts=0,
                declining_activity_contacts=0,
                insufficient_data_contacts=0,
            ),
            contacts=[],
        )

    current_time = _as_utc(as_of or datetime.now(timezone.utc))
    recent_start = current_time - timedelta(days=FORGOTTEN_RECENT_WINDOW_DAYS)

    peers_statement = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Message.sender_telegram_id.label("peer_telegram_user_id"),
        )
        .join(Message, Message.chat_id == Chat.id)
        .join(TelegramAccount, TelegramAccount.id == Chat.account_id)
        .where(
            Chat.chat_type == "personal_chat",
            TelegramAccount.telegram_user_id.is_not(None),
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.sender_telegram_id.is_not(None),
            Message.sender_telegram_id != TelegramAccount.telegram_user_id,
        )
        .distinct()
    )
    if account_id is not None:
        peers_statement = peers_statement.where(Chat.account_id == account_id)
    peers = peers_statement.cte("forgotten_contact_peers")
    single_peer_chats = (
        select(peers.c.chat_id)
        .group_by(peers.c.chat_id)
        .having(func.count() == 1)
        .cte("forgotten_single_peer_chats")
    )
    eligible_pairs = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Contact.id.label("contact_id"),
            Contact.telegram_user_id.label("contact_telegram_user_id"),
            TelegramAccount.telegram_user_id.label("owner_telegram_user_id"),
            Contact.display_name.label("display_name"),
        )
        .join(TelegramAccount, TelegramAccount.id == Chat.account_id)
        .join(peers, peers.c.chat_id == Chat.id)
        .join(single_peer_chats, single_peer_chats.c.chat_id == Chat.id)
        .join(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.telegram_user_id == peers.c.peer_telegram_user_id,
            ),
        )
        .cte("forgotten_eligible_pairs")
    )

    ordinary_message = Message.message_type == ORDINARY_MESSAGE_TYPE
    owner_direction = and_(
        Message.sender_telegram_id == eligible_pairs.c.owner_telegram_user_id,
        Message.is_outgoing.is_(True),
    )
    contact_direction = and_(
        Message.sender_telegram_id == eligible_pairs.c.contact_telegram_user_id,
        Message.is_outgoing.is_(False),
    )
    known_direction = or_(owner_direction, contact_direction)
    historical_message = and_(
        Message.message_date < recent_start,
        Message.message_date <= current_time,
    )
    recent_message = and_(
        Message.message_date >= recent_start,
        Message.message_date <= current_time,
    )
    dated_message = Message.message_date <= current_time
    utc_message_date = (
        func.date(func.timezone("UTC", Message.message_date))
        if db.get_bind().dialect.name == "postgresql"
        else func.date(Message.message_date)
    )
    text_length = func.length(func.coalesce(Message.text_content, ""))

    def count_when(condition):
        return func.coalesce(
            func.sum(case((condition, 1), else_=0)),
            0,
        )

    aggregate_statement = (
        select(
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            eligible_pairs.c.contact_telegram_user_id.label("telegram_user_id"),
            eligible_pairs.c.display_name,
            count_when(and_(ordinary_message, owner_direction)).label(
                "owner_message_count"
            ),
            count_when(and_(ordinary_message, contact_direction)).label(
                "contact_message_count"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (and_(ordinary_message, owner_direction), text_length),
                        else_=0,
                    )
                ),
                0,
            ).label("owner_text_length"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(ordinary_message, contact_direction), text_length),
                        else_=0,
                    )
                ),
                0,
            ).label("contact_text_length"),
            func.count(
                case((and_(ordinary_message, known_direction), Message.id))
            ).label("known_message_count"),
            func.count(case((ordinary_message, Message.id))).label(
                "ordinary_message_count"
            ),
            func.min(
                case(
                    (and_(ordinary_message, known_direction, dated_message), Message.message_date)
                )
            ).label("first_message_at"),
            func.max(
                case(
                    (and_(ordinary_message, known_direction, dated_message), Message.message_date)
                )
            ).label("last_message_at"),
            func.count(
                func.distinct(
                    case(
                        (
                            and_(ordinary_message, known_direction, dated_message),
                            utc_message_date,
                        )
                    )
                )
            ).label("distinct_active_days"),
            count_when(
                and_(ordinary_message, known_direction, historical_message)
            ).label("historical_message_count"),
            func.min(
                case(
                    (
                        and_(ordinary_message, known_direction, historical_message),
                        Message.message_date,
                    )
                )
            ).label("historical_first_message_at"),
            func.max(
                case(
                    (
                        and_(ordinary_message, known_direction, historical_message),
                        Message.message_date,
                    )
                )
            ).label("historical_last_message_at"),
            func.count(
                func.distinct(
                    case(
                        (
                            and_(
                                ordinary_message,
                                known_direction,
                                historical_message,
                            ),
                            utc_message_date,
                        )
                    )
                )
            ).label("historical_active_days"),
            count_when(and_(ordinary_message, owner_direction, recent_message)).label(
                "recent_owner_message_count"
            ),
            count_when(
                and_(ordinary_message, contact_direction, recent_message)
            ).label("recent_contact_message_count"),
        )
        .select_from(eligible_pairs)
        .join(Message, Message.chat_id == eligible_pairs.c.chat_id)
        .group_by(
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            eligible_pairs.c.contact_telegram_user_id,
            eligible_pairs.c.display_name,
        )
    )

    month_expression = _utc_month_expression(db)
    historical_month = and_(
        ordinary_message,
        known_direction,
        historical_message,
    )
    recent_month = and_(
        ordinary_message,
        known_direction,
        recent_message,
    )
    monthly_statement = (
        select(
            eligible_pairs.c.contact_id,
            month_expression.label("month"),
            count_when(and_(historical_month, owner_direction)).label(
                "historical_owner_message_count"
            ),
            count_when(and_(historical_month, contact_direction)).label(
                "historical_contact_message_count"
            ),
            count_when(and_(recent_month, owner_direction)).label(
                "recent_owner_message_count"
            ),
            count_when(and_(recent_month, contact_direction)).label(
                "recent_contact_message_count"
            ),
        )
        .select_from(eligible_pairs)
        .join(Message, Message.chat_id == eligible_pairs.c.chat_id)
        .where(Message.message_date.is_not(None), dated_message)
        .group_by(eligible_pairs.c.contact_id, month_expression)
        .order_by(eligible_pairs.c.contact_id, month_expression)
    )

    monthly_by_contact: dict[int, list[dict[str, int | str]]] = {}
    for month_row in db.execute(monthly_statement):
        monthly_by_contact.setdefault(month_row.contact_id, []).append(
            {
                "month": month_row.month,
                "historical_owner_message_count": int(
                    month_row.historical_owner_message_count
                ),
                "historical_contact_message_count": int(
                    month_row.historical_contact_message_count
                ),
                "recent_owner_message_count": int(
                    month_row.recent_owner_message_count
                ),
                "recent_contact_message_count": int(
                    month_row.recent_contact_message_count
                ),
            }
        )

    contacts: list[ForgottenContact] = []
    for row in db.execute(aggregate_statement):
        owner_message_count = int(row.owner_message_count)
        contact_message_count = int(row.contact_message_count)
        owner_text_length = int(row.owner_text_length)
        contact_text_length = int(row.contact_text_length)
        recent_owner_count = int(row.recent_owner_message_count)
        recent_contact_count = int(row.recent_contact_message_count)
        recent_count = recent_owner_count + recent_contact_count
        historical_count = int(row.historical_message_count)
        excluded_ambiguous_count = (
            int(row.ordinary_message_count) - int(row.known_message_count)
        )
        first_message_at = (
            _as_utc(row.first_message_at) if row.first_message_at is not None else None
        )
        last_message_at = (
            _as_utc(row.last_message_at) if row.last_message_at is not None else None
        )
        historical_first = (
            _as_utc(row.historical_first_message_at)
            if row.historical_first_message_at is not None
            else None
        )
        historical_last = (
            _as_utc(row.historical_last_message_at)
            if row.historical_last_message_at is not None
            else None
        )
        days_since_last = (
            max(0, (current_time - last_message_at).days)
            if last_message_at is not None
            else None
        )

        historical_months: list[ForgottenContactMonthlyActivity] = []
        recent_months: list[ForgottenContactMonthlyActivity] = []
        monthly_rows = monthly_by_contact.get(row.contact_id, [])
        historical_active_month_count = 0
        for month_row in monthly_rows:
            historical_owner = int(month_row["historical_owner_message_count"])
            historical_contact = int(month_row["historical_contact_message_count"])
            recent_owner = int(month_row["recent_owner_message_count"])
            recent_contact = int(month_row["recent_contact_message_count"])
            historical_total = historical_owner + historical_contact
            recent_total = recent_owner + recent_contact
            if historical_total:
                historical_active_month_count += 1
                historical_months.append(
                    ForgottenContactMonthlyActivity(
                        month=str(month_row["month"]),
                        owner_message_count=historical_owner,
                        contact_message_count=historical_contact,
                        total_message_count=historical_total,
                    )
                )
            if recent_total:
                recent_months.append(
                    ForgottenContactMonthlyActivity(
                        month=str(month_row["month"]),
                        owner_message_count=recent_owner,
                        contact_message_count=recent_contact,
                        total_message_count=recent_total,
                    )
                )

        meaningful_history = (
            historical_count >= FORGOTTEN_MIN_HISTORICAL_MESSAGES
            and int(row.historical_active_days)
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_DAYS
            and historical_active_month_count
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_MONTHS
        )
        historical_span_days = (
            (historical_last - historical_first).total_seconds() / 86400
            if historical_first is not None and historical_last is not None
            else 0.0
        )
        reliable_baseline = (
            meaningful_history
            and historical_span_days >= FORGOTTEN_MIN_BASELINE_SPAN_DAYS
            and excluded_ambiguous_count == 0
        )

        if excluded_ambiguous_count:
            evidence_status: ForgottenContactEvidenceStatus = "ambiguous_direction"
        elif not meaningful_history:
            evidence_status = "insufficient_history"
        elif not reliable_baseline:
            evidence_status = "insufficient_baseline"
        else:
            evidence_status = "reliable_baseline"

        historical_monthly_baseline = None
        activity_decline_percentage = None
        ranking_score = None
        recent_monthly_activity = (
            recent_count
            / FORGOTTEN_RECENT_WINDOW_DAYS
            * FORGOTTEN_RECENT_MONTH_DAYS
        )
        if reliable_baseline and historical_span_days > 0:
            historical_monthly_baseline = (
                historical_count
                / historical_span_days
                * FORGOTTEN_RECENT_MONTH_DAYS
            )
            if historical_monthly_baseline > 0:
                decline_fraction = max(
                    0.0,
                    min(
                        1.0,
                        1.0
                        - recent_monthly_activity / historical_monthly_baseline,
                    ),
                )
                activity_decline_percentage = decline_fraction * 100
                if days_since_last is not None:
                    historical_evidence = min(
                        1.0,
                        historical_count / FORGOTTEN_EVIDENCE_MESSAGE_CAP,
                    )
                    inactivity_factor = min(
                        1.0,
                        days_since_last / FORGOTTEN_SCORE_INACTIVITY_CAP_DAYS,
                    )
                    ranking_score = round(
                        100
                        * historical_evidence
                        * (
                            FORGOTTEN_SCORE_INACTIVITY_WEIGHT * inactivity_factor
                            + FORGOTTEN_SCORE_DECLINE_WEIGHT * decline_fraction
                        ),
                        2,
                    )

        if evidence_status != "reliable_baseline" or days_since_last is None:
            classification = "insufficient_data"
        elif days_since_last >= FORGOTTEN_INACTIVE_DAYS:
            classification = "inactive"
        elif (
            activity_decline_percentage is not None
            and activity_decline_percentage
            >= FORGOTTEN_DECLINE_THRESHOLD * 100
        ):
            classification = "activity_declined"
        else:
            classification = "active"

        contacts.append(
            ForgottenContact(
                account_id=row.account_id,
                contact_id=row.contact_id,
                telegram_user_id=row.telegram_user_id,
                display_name=row.display_name,
                first_message_at=first_message_at,
                last_message_at=last_message_at,
                days_since_last_communication=days_since_last,
                owner_message_count=owner_message_count,
                contact_message_count=contact_message_count,
                total_message_count=owner_message_count + contact_message_count,
                excluded_ambiguous_message_count=excluded_ambiguous_count,
                owner_text_length=owner_text_length,
                contact_text_length=contact_text_length,
                total_text_length=owner_text_length + contact_text_length,
                distinct_active_days=int(row.distinct_active_days),
                historical_message_count=historical_count,
                historical_active_days=int(row.historical_active_days),
                historical_active_month_count=historical_active_month_count,
                historical_activity_by_month=historical_months,
                recent_activity_by_month=recent_months,
                recent_owner_message_count=recent_owner_count,
                recent_contact_message_count=recent_contact_count,
                recent_message_count=recent_count,
                historical_monthly_baseline=(
                    round(historical_monthly_baseline, 2)
                    if historical_monthly_baseline is not None
                    else None
                ),
                recent_monthly_activity=round(recent_monthly_activity, 2),
                activity_decline_percentage=(
                    round(activity_decline_percentage, 2)
                    if activity_decline_percentage is not None
                    else None
                ),
                classification=classification,
                evidence_status=evidence_status,
                ranking_score=ranking_score,
            )
        )

    if sort_by == "display_name":
        contacts.sort(
            key=lambda contact: (
                contact.classification == "insufficient_data",
                (contact.display_name or "").casefold(),
                contact.contact_id,
            )
        )
    elif sort_by == "days_since_last_communication":
        contacts.sort(
            key=lambda contact: (
                contact.days_since_last_communication is None,
                -(contact.days_since_last_communication or 0),
                contact.contact_id,
            )
        )
    elif sort_by == "historical_message_count":
        contacts.sort(
            key=lambda contact: (
                -contact.historical_message_count,
                contact.contact_id,
            )
        )
    else:
        contacts.sort(
            key=lambda contact: (
                contact.ranking_score is None,
                -(contact.ranking_score or 0.0),
                contact.contact_id,
            )
        )

    summary = ForgottenContactsSummary(
        account_id=account_id,
        eligible_contacts=len(contacts),
        meaningful_historical_contacts=sum(
            contact.historical_message_count >= FORGOTTEN_MIN_HISTORICAL_MESSAGES
            and contact.historical_active_days
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_DAYS
            and contact.historical_active_month_count
            >= FORGOTTEN_MIN_HISTORICAL_ACTIVE_MONTHS
            for contact in contacts
        ),
        currently_inactive_contacts=sum(
            contact.days_since_last_communication is not None
            and contact.days_since_last_communication >= FORGOTTEN_INACTIVE_DAYS
            for contact in contacts
        ),
        declining_activity_contacts=sum(
            contact.activity_decline_percentage is not None
            and contact.activity_decline_percentage
            >= FORGOTTEN_DECLINE_THRESHOLD * 100
            for contact in contacts
        ),
        insufficient_data_contacts=sum(
            contact.classification == "insufficient_data" for contact in contacts
        ),
    )
    return ForgottenContactsStatistics(
        summary=summary,
        contacts=contacts[:limit],
    )


@router.get(
    "/forgotten-contacts",
    response_model=ForgottenContactsStatistics,
    summary="Rank private contacts by inactivity and declining communication",
    description=(
        "Uses only ordinary messages in 'personal_chat' chats with a known "
        "account owner, exactly one non-owner sender ID, and a matching "
        "account-local contact. Sender ID and is_outgoing must agree; contacts "
        "with any ambiguous ordinary-message direction are returned without a "
        "score. Group chats are excluded. The recent window is the trailing "
        "90 days ending at request time. Historical evidence requires at least "
        "20 known-direction messages, five active UTC days, and three active "
        "pre-window months; a score additionally requires a 90-day historical "
        "span and no ambiguous messages. Monthly activity splits each UTC "
        "calendar month at the exact 90-day cutoff, so partial months are not "
        "compared as if complete. The baseline is historical messages per "
        "30 days across the dated pre-window activity span. Decline is "
        "max(0, 1 - recent monthly rate / historical monthly rate), capped at "
        "100%; 50% is the decline threshold. Score is 100 times min(historical "
        "messages / 100, 1) times (0.60 * min(days inactive / 180, 1) + "
        "0.40 * decline fraction). These descriptive thresholds are "
        "heuristics, not judgments about relationships."
    ),
)
def get_forgotten_contacts(
    db: Session = Depends(get_db),
    account_id: int | None = Query(default=None, gt=0),
    sort_by: Literal[
        "ranking_score",
        "display_name",
        "days_since_last_communication",
        "historical_message_count",
    ] = Query(default="ranking_score"),
    limit: int = Query(default=100, ge=1, le=FORGOTTEN_MAX_LIMIT),
) -> ForgottenContactsStatistics:
    return build_forgotten_contacts_statistics(
        db,
        account_id=account_id,
        sort_by=sort_by,
        limit=limit,
    )