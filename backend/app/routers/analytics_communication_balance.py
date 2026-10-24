from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Account, CanonicalIdentity, Chat, Contact, Message
from app.platforms import TELEGRAM_PLATFORM_ID
from app.schemas.analytics import (
    CommunicationBalanceClassification,
    CommunicationBalanceContact,
    CommunicationBalanceStatistics,
    CommunicationBalanceSummary,
)

from .analytics_constants import (
    ORDINARY_MESSAGE_TYPE,
    MINIMUM_BALANCE_TEXT_LENGTH,
    BALANCED_OWNER_SHARE_MINIMUM,
    BALANCED_OWNER_SHARE_MAXIMUM,
    STRONG_OWNER_SHARE_MINIMUM,
    STRONG_CONTACT_OWNER_SHARE_MAXIMUM,
)

router = APIRouter()


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
        "only when chat_type is 'personal_chat', at least one owner alias is "
        "known, and exactly one non-owner sender ID in ordinary messages "
        "resolves to a canonical contact identity; matching identities are "
        "combined across source accounts. "
        "group chats and ambiguous records are excluded. Any known owner alias "
        "counts as owner-sent regardless of source-local is_outgoing flags; "
        "contact messages require a matching sender ID and is_outgoing=false."
    ),
)
def get_communication_balance(
    db: Session = Depends(get_db),
    sort_by: Literal["display_name", "owner_share", "message_count"] = Query(
        default="display_name",
        description="Sort by display name, owner text share ascending, or known-direction message count descending.",
    ),
) -> CommunicationBalanceStatistics:
    owner_ids = select(Account.platform_user_id).where(
        Account.platform == TELEGRAM_PLATFORM_ID,
        Account.platform_user_id.is_not(None)
    )
    peers = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Message.sender_id.label("peer_telegram_user_id"),
        )
        .join(Message, Message.chat_id == Chat.id)
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == TELEGRAM_PLATFORM_ID,
            Account.platform == TELEGRAM_PLATFORM_ID,
            Message.platform == TELEGRAM_PLATFORM_ID,
            Chat.chat_type == "personal_chat",
            Account.platform_user_id.is_not(None),
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.sender_id.is_not(None),
            Message.sender_id.not_in(owner_ids),
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
            func.coalesce(CanonicalIdentity.id, -Contact.id).label(
                "identity_group_id"
            ),
            case(
                (CanonicalIdentity.id.is_(None), Chat.account_id),
                else_=None,
            ).label("identity_source_account_id"),
            CanonicalIdentity.id.label("canonical_identity_id"),
            Contact.id.label("contact_id"),
            Contact.platform_user_id.label("contact_platform_user_id"),
            Contact.display_name.label("display_name"),
        )
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == TELEGRAM_PLATFORM_ID,
            Account.platform == TELEGRAM_PLATFORM_ID,
        )
        .join(peers, peers.c.chat_id == Chat.id)
        .join(single_peer_chats, single_peer_chats.c.chat_id == Chat.id)
        .join(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.platform == TELEGRAM_PLATFORM_ID,
                Contact.platform_user_id == peers.c.peer_telegram_user_id,
            ),
        )
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
        .cte("eligible_private_chat_pairs")
    )

    is_ordinary = Message.message_type == ORDINARY_MESSAGE_TYPE
    owner_direction = Message.sender_id.in_(owner_ids)
    contact_direction = and_(
        Message.sender_id == eligible_pairs.c.contact_platform_user_id,
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
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            func.min(eligible_pairs.c.contact_id).label("contact_id"),
            func.min(eligible_pairs.c.canonical_identity_id).label(
                "canonical_identity_id"
            ),
            eligible_pairs.c.contact_platform_user_id.label("platform_user_id"),
            func.min(eligible_pairs.c.display_name).label("display_name"),
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
        .where(Message.platform == TELEGRAM_PLATFORM_ID)
        .group_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            eligible_pairs.c.contact_platform_user_id,
        )
        .having(func.count(case((is_ordinary, Message.id))) > 0)
    )

    source_rows = db.execute(
        select(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            Account.username.label("account_username"),
            Account.name.label("account_name"),
        ).distinct()
        .join(Account, Account.id == eligible_pairs.c.account_id)
    )
    source_ids: dict[
        tuple[int, int | None], tuple[set[int], set[int], set[str]]
    ] = {}
    for source_row in source_rows:
        key = (
            source_row.identity_group_id,
            source_row.identity_source_account_id,
        )
        accounts, contact_ids, account_labels = source_ids.setdefault(
            key, (set(), set(), set())
        )
        accounts.add(source_row.account_id)
        contact_ids.add(source_row.contact_id)
        account_labels.add(
            f"@{source_row.account_username}"
            if source_row.account_username
            else source_row.account_name
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
        source_account_ids, source_contact_ids, source_account_labels = source_ids[
            (row.identity_group_id, row.identity_source_account_id)
        ]
        contacts.append(
            CommunicationBalanceContact(
                account_id=(
                    min(source_account_ids)
                    if len(source_account_ids) == 1
                    else None
                ),
                contact_id=row.contact_id,
                canonical_identity_id=row.canonical_identity_id,
                source_account_ids=sorted(source_account_ids),
                source_account_labels=sorted(source_account_labels),
                source_contact_ids=sorted(source_contact_ids),
                platform_user_id=row.platform_user_id,
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
