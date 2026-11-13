from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.constants import DEFAULT_PAGE_SIZE
from app.db import get_db
from app.models import Account, CanonicalIdentity, Chat, Contact, Message
from app.schemas.analytics import (
    CommunicationBalanceClassification,
    CommunicationBalanceContact,
    CommunicationBalanceStatistics,
    CommunicationBalanceSummary,
    PaginationMetadata,
    SearchOption,
)

from app.constants import (
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
        "Compares normalized text volume in eligible one-to-one personal chats "
        "across source accounts. Explicitly linked identities are combined; "
        "unlinked identities remain separate. Text length is the number of Unicode code points "
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
    sort_by: Literal["text_volume", "owner_share", "recent_activity"] = Query(
        default="text_volume",
        description="Sort by total text volume, owner text share, or recent activity.",
    ),
    sort_direction: Literal["asc", "desc"] = "asc",
    classification: CommunicationBalanceClassification | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = DEFAULT_PAGE_SIZE,
) -> CommunicationBalanceStatistics:
    owner_account = aliased(Account)
    owner_sender = (
        select(owner_account.id)
        .where(
            owner_account.platform == Message.platform,
            owner_account.platform_user_id == Message.sender_id,
        )
        .exists()
    )
    peers = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Message.sender_id.label("peer_platform_user_id"),
        )
        .join(Message, Message.chat_id == Chat.id)
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == Account.platform,
            Message.platform == Chat.platform,
            Chat.chat_type == "personal_chat",
            Account.platform_user_id.is_not(None),
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.sender_id.is_not(None),
            ~owner_sender,
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
            CanonicalIdentity.identity_group_id.label("identity_group_id"),
            case(
                (
                    CanonicalIdentity.identity_group_id.is_(None),
                    CanonicalIdentity.id,
                ),
                else_=None,
            ).label("canonical_identity_id"),
            case(
                (
                    and_(
                        CanonicalIdentity.identity_group_id.is_(None),
                        CanonicalIdentity.id.is_(None),
                    ),
                    Contact.id,
                ),
                else_=None,
            ).label("identity_contact_id"),
            case(
                (
                    and_(
                        CanonicalIdentity.identity_group_id.is_(None),
                        CanonicalIdentity.id.is_(None),
                    ),
                    Chat.account_id,
                ),
                else_=None,
            ).label("identity_source_account_id"),
            Contact.id.label("contact_id"),
            Contact.platform.label("platform"),
            Contact.platform_user_id.label("contact_platform_user_id"),
            Contact.display_name.label("display_name"),
        )
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == Account.platform,
        )
        .join(peers, peers.c.chat_id == Chat.id)
        .join(single_peer_chats, single_peer_chats.c.chat_id == Chat.id)
        .join(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.platform == Chat.platform,
                Contact.platform_user_id == peers.c.peer_platform_user_id,
            ),
        )
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
        .cte("eligible_private_chat_pairs")
    )

    is_ordinary = Message.message_type == ORDINARY_MESSAGE_TYPE
    owner_direction = (
        select(owner_account.id)
        .where(
            owner_account.platform == Message.platform,
            owner_account.platform_user_id == Message.sender_id,
        )
        .exists()
    )
    contact_direction = and_(
        Message.platform == eligible_pairs.c.platform,
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
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
            eligible_pairs.c.identity_source_account_id,
            func.min(eligible_pairs.c.contact_id).label("contact_id"),
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
        .where(Message.platform == eligible_pairs.c.platform)
        .group_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
            eligible_pairs.c.identity_source_account_id,
        )
        .having(func.count(case((is_ordinary, Message.id))) > 0)
    )

    source_rows = db.execute(
        select(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
            eligible_pairs.c.identity_source_account_id,
            eligible_pairs.c.account_id,
            eligible_pairs.c.contact_id,
            eligible_pairs.c.platform,
            eligible_pairs.c.contact_platform_user_id,
            Account.username.label("account_username"),
            Account.name.label("account_name"),
        ).distinct()
        .join(Account, Account.id == eligible_pairs.c.account_id)
    )
    source_ids: dict[tuple[int | None, int | None, int | None, int | None], tuple[set[int], set[int], set[str], set[str], set[str], set[int]]] = {}
    for source_row in source_rows:
        key = (
            source_row.identity_group_id,
            source_row.canonical_identity_id,
            source_row.identity_contact_id,
            source_row.identity_source_account_id,
        )
        accounts, contact_ids, account_labels, platforms, user_ids, identity_ids = source_ids.setdefault(
            key, (set(), set(), set(), set(), set(), set())
        )
        accounts.add(source_row.account_id)
        contact_ids.add(source_row.contact_id)
        platforms.add(source_row.platform)
        user_ids.add(source_row.contact_platform_user_id)
        if source_row.canonical_identity_id is not None:
            identity_ids.add(source_row.canonical_identity_id)
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
        (
            source_account_ids,
            source_contact_ids,
            source_account_labels,
            platforms,
            platform_user_ids,
            identity_ids,
        ) = source_ids[
            (
                row.identity_group_id,
                row.canonical_identity_id,
                row.identity_contact_id,
                row.identity_source_account_id,
            )
        ]
        contacts.append(
            CommunicationBalanceContact(
                account_id=(
                    min(source_account_ids)
                    if len(source_account_ids) == 1
                    else None
                ),
                contact_id=row.contact_id,
                canonical_identity_id=min(identity_ids) if identity_ids else None,
                identity_group_id=row.identity_group_id,
                platforms=sorted(platforms),
                source_account_ids=sorted(source_account_ids),
                source_account_labels=sorted(source_account_labels),
                source_contact_ids=sorted(source_contact_ids),
                platform_user_ids=sorted(platform_user_ids),
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
        sortable = [contact for contact in contacts if contact.owner_text_share is not None]
        unsortable = [contact for contact in contacts if contact.owner_text_share is None]
        sortable.sort(
            key=lambda contact: (
                contact.owner_text_share,
                (contact.display_name or "").casefold(),
                contact.contact_id,
            ),
            reverse=sort_direction == "desc",
        )
    elif sort_by == "recent_activity":
        sortable = [contact for contact in contacts if contact.last_message_at is not None]
        unsortable = [contact for contact in contacts if contact.last_message_at is None]
        sortable.sort(
            key=lambda contact: (
                (
                    contact.last_message_at.isoformat()
                    if contact.last_message_at is not None
                    else ""
                ),
                (contact.display_name or "").casefold(),
                contact.contact_id,
            ),
            reverse=sort_direction == "desc",
        )
    else:
        sortable = contacts
        unsortable = []
        sortable.sort(
            key=lambda contact: (
                contact.total_text_length,
                (contact.display_name or "").casefold(),
                contact.contact_id,
            ),
            reverse=sort_direction == "desc",
        )
    contacts = sortable + unsortable

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
    filtered_contacts = [
        contact
        for contact in contacts
        if classification is None or contact.classification == classification
    ]
    offset = (page - 1) * page_size
    return CommunicationBalanceStatistics(
        summary=summary,
        contacts=filtered_contacts[offset : offset + page_size],
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=len(filtered_contacts),
        ),
        options=[
            SearchOption(
                value=str(index),
                label=contact.display_name or "Unnamed contact",
                platforms=contact.platforms,
                search_terms=[
                    *contact.platform_user_ids,
                    *contact.source_account_labels,
                ],
            )
            for index, contact in enumerate(filtered_contacts)
        ],
    )
