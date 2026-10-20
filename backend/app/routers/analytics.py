from typing import Literal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query

from app.db import get_db
from app.models import Chat, Contact, Message, TelegramAccount
from app.schemas.analytics import (
    ChatStatistics,
    CommunicationBalanceClassification,
    CommunicationBalanceContact,
    CommunicationBalanceStatistics,
    CommunicationBalanceSummary,
    ContactStatistics,
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