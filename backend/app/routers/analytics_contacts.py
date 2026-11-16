from typing import Annotated, Literal, TypedDict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.constants import (
    DEFAULT_PAGE_SIZE,
    ORDINARY_MESSAGE_TYPE,
    SERVICE_MESSAGE_TYPE,
)
from app.db import get_db
from app.models import Account, CanonicalIdentity, Chat, Contact, Message
from app.routers.analytics_friendship import (
    build_friendship_analytics,
    contact_group_key,
)
from app.schemas.analytics import (
    ContactAccountSource,
    ContactStatistics,
    PaginatedItems,
    PaginationMetadata,
    SearchOption,
)

router = APIRouter()


class ContactGroup(TypedDict):
    friend_key: tuple[object, ...]
    platforms: set[str]
    identity_ids: set[int]
    identity_group_id: int | None
    platform_user_ids: set[str]
    display_names: set[str]
    source_account_ids: set[int]
    source_account_labels: set[str]
    source_accounts: set[tuple[str, str]]
    source_contact_ids: set[int]
    total_messages_sent: int
    personal_chat_messages_sent: int
    group_chat_messages_sent: int
    ordinary_messages_sent: int
    service_events_attributed: int


@router.get(
    "/contacts",
    response_model=PaginatedItems[ContactStatistics],
    summary="Get communication statistics by sender/contact",
    description=(
        "Returns a page of contacts and lightweight options for searching all "
        "contacts. Contacts are combined across source accounts and explicitly linked "
        "platform identities. Unlinked identities remain separate and "
        "unidentified senders remain account-local. Contacts without messages "
        "are included with zero counts. Incoming counts require reliable "
        "incoming direction; ordinary and service counts are reported "
        "separately. Total sender-attributed messages are also split between "
        "personal_chat and non-one-to-one chats. Results can be sorted by total, "
        "DM, or group messages. An optional platform filter limits contacts and "
        "pagination to identities associated with that platform. Friend statuses "
        "use dated, non-empty ordinary text messages in unambiguous personal "
        "chats: Active requires at least 20 exchanged messages in the previous "
        "six calendar months and an owner-sent message; Close requires at least "
        "200 exchanged messages in a complete UTC year, an owner-sent message "
        "each following year, and owner contact within the previous 12 months. "
        "Active is independent and can coexist with Close or exClose. exClose "
        "indicates historical Close status without current Close continuity. "
        "The optional friend_status filter includes contacts carrying that status."
    ),
)
def get_contact_statistics(
    db: Session = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = DEFAULT_PAGE_SIZE,
    platform: str | None = None,
    friend_status: Literal["Active", "Close", "exClose"] | None = None,
    sort_by: Literal[
        "total_messages_sent",
        "personal_chat_messages_sent",
        "group_chat_messages_sent",
    ] = "total_messages_sent",
    sort_direction: Literal["asc", "desc"] = "desc",
) -> PaginatedItems[ContactStatistics]:
    owner_account = aliased(Account)
    sender_id = Message.sender_id
    is_owner = (
        select(owner_account.id)
        .where(
            owner_account.platform == Message.platform,
            owner_account.platform_user_id == sender_id,
        )
        .exists()
    )
    message_groups = (
        select(
            Chat.account_id.label("account_id"),
            Message.platform.label("platform"),
            Message.sender_contact_id.label("sender_contact_id"),
            Message.sender_id.label("platform_user_id"),
            func.count(Message.id).label("total_messages_sent"),
            func.count(
                case(
                    (Chat.chat_type == "personal_chat", Message.id),
                )
            ).label("personal_chat_messages_sent"),
            func.count(
                case(
                    (Chat.chat_type != "personal_chat", Message.id),
                )
            ).label("group_chat_messages_sent"),
            func.count(
                case((Message.message_type == ORDINARY_MESSAGE_TYPE, Message.id))
            ).label("ordinary_messages_sent"),
            func.count(
                case((Message.message_type == SERVICE_MESSAGE_TYPE, Message.id))
            ).label("service_events_attributed"),
        )
        .select_from(Message)
        .join(Chat, Message.chat_id == Chat.id)
        .join(Account, Chat.account_id == Account.id)
        .where(
            Chat.platform == Account.platform,
            Message.platform == Account.platform,
            Message.is_outgoing.is_(False),
            or_(sender_id.is_(None), ~is_owner),
        )
        .group_by(
            Chat.account_id,
            Message.platform,
            Message.sender_contact_id,
            Message.sender_id,
        )
        .subquery()
    )
    statement = (
        select(
            message_groups.c.account_id,
            message_groups.c.platform,
            Account.username.label("account_username"),
            Account.name.label("account_name"),
            Contact.id.label("contact_id"),
            CanonicalIdentity.id.label("canonical_identity_id"),
            CanonicalIdentity.identity_group_id.label("identity_group_id"),
            message_groups.c.platform_user_id,
            Contact.display_name.label("display_name"),
            message_groups.c.total_messages_sent,
            message_groups.c.personal_chat_messages_sent,
            message_groups.c.group_chat_messages_sent,
            message_groups.c.ordinary_messages_sent,
            message_groups.c.service_events_attributed,
        )
        .select_from(message_groups)
        .join(Account, Account.id == message_groups.c.account_id)
        .outerjoin(
            Contact,
            and_(
                Contact.account_id == message_groups.c.account_id,
                Contact.platform == message_groups.c.platform,
                or_(
                    Contact.id == message_groups.c.sender_contact_id,
                    and_(
                        message_groups.c.sender_contact_id.is_(None),
                        message_groups.c.platform_user_id.is_not(None),
                        Contact.platform_user_id == message_groups.c.platform_user_id,
                    ),
                ),
            ),
        )
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
    )
    groups: dict[tuple[object, ...], ContactGroup] = {}

    def add_source(
        key: tuple[object, ...],
        *,
        platform: str,
        account_id: int,
        account_label: str,
        contact_id: int | None,
        identity_id: int | None,
        identity_group_id: int | None,
        platform_user_id: str | None,
        display_name: str | None,
    ) -> ContactGroup:
        group = groups.setdefault(
            key,
            {
                "platforms": set(),
                "friend_key": key,
                "identity_ids": set(),
                "identity_group_id": identity_group_id,
                "platform_user_ids": set(),
                "display_names": set(),
                "source_account_ids": set(),
                "source_account_labels": set(),
                "source_accounts": set(),
                "source_contact_ids": set(),
                "total_messages_sent": 0,
                "personal_chat_messages_sent": 0,
                "group_chat_messages_sent": 0,
                "ordinary_messages_sent": 0,
                "service_events_attributed": 0,
            },
        )
        group["platforms"].add(platform)
        if identity_id is not None:
            group["identity_ids"].add(identity_id)
        if platform_user_id is not None:
            group["platform_user_ids"].add(platform_user_id)
        if display_name:
            group["display_names"].add(display_name)
        group["source_account_ids"].add(account_id)
        group["source_account_labels"].add(account_label)
        group["source_accounts"].add((platform, account_label))
        if contact_id is not None:
            group["source_contact_ids"].add(contact_id)
        return group

    for row in db.execute(statement):
        account_label = (
            f"@{row.account_username}" if row.account_username else row.account_name
        )
        key = contact_group_key(
            row.platform,
            row.account_id,
            row.contact_id,
            row.canonical_identity_id,
            row.identity_group_id,
            row.platform_user_id,
        )
        group = add_source(
            key,
            platform=row.platform,
            account_id=row.account_id,
            account_label=account_label,
            contact_id=row.contact_id,
            identity_id=row.canonical_identity_id,
            identity_group_id=row.identity_group_id,
            platform_user_id=row.platform_user_id,
            display_name=row.display_name,
        )
        group["total_messages_sent"] += int(row.total_messages_sent)
        group["personal_chat_messages_sent"] += int(
            row.personal_chat_messages_sent
        )
        group["group_chat_messages_sent"] += int(row.group_chat_messages_sent)
        group["ordinary_messages_sent"] += int(row.ordinary_messages_sent)
        group["service_events_attributed"] += int(row.service_events_attributed)

    owner_ids_by_platform: dict[str, set[str]] = {}
    for owner_platform, user_id in db.execute(
        select(Account.platform, Account.platform_user_id).where(
            Account.platform_user_id.is_not(None)
        )
    ):
        if user_id is not None:
            owner_ids_by_platform.setdefault(owner_platform, set()).add(user_id)

    for contact, account, identity_group_id in db.execute(
        select(Contact, Account, CanonicalIdentity.identity_group_id)
        .join(Account, Account.id == Contact.account_id)
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
        .where(Contact.platform == Account.platform)
    ):
        if contact.platform_user_id in owner_ids_by_platform.get(
            contact.platform,
            set(),
        ):
            continue
        key = contact_group_key(
            contact.platform,
            account.id,
            contact.id,
            contact.canonical_identity_id,
            identity_group_id,
            contact.platform_user_id,
        )
        add_source(
            key,
            platform=contact.platform,
            account_id=account.id,
            account_label=f"@{account.username}" if account.username else account.name,
            contact_id=contact.id,
            identity_id=contact.canonical_identity_id,
            identity_group_id=identity_group_id,
            platform_user_id=contact.platform_user_id,
            display_name=contact.display_name,
        )

    friend_analytics = build_friendship_analytics(db)
    contacts = []
    for group in groups.values():
        source_account_ids = sorted(group["source_account_ids"])
        source_contact_ids = sorted(group["source_contact_ids"])
        display_names = sorted(group["display_names"], key=str.casefold)
        contacts.append(
            ContactStatistics(
                friend_statuses=friend_analytics.statuses_by_contact.get(
                    group["friend_key"],
                    [],
                ),
                platforms=sorted(group["platforms"]),
                account_id=(
                    source_account_ids[0] if len(source_account_ids) == 1 else None
                ),
                identity_group_id=group["identity_group_id"],
                canonical_identity_id=min(group["identity_ids"])
                if group["identity_ids"]
                else None,
                source_account_ids=source_account_ids,
                source_account_labels=sorted(group["source_account_labels"]),
                source_accounts=[
                    ContactAccountSource(platform=platform, label=label)
                    for platform, label in sorted(group["source_accounts"])
                ],
                source_contact_ids=source_contact_ids,
                platform_user_ids=sorted(group["platform_user_ids"]),
                display_name=display_names[0] if display_names else None,
                total_messages_sent=group["total_messages_sent"],
                personal_chat_messages_sent=group["personal_chat_messages_sent"],
                group_chat_messages_sent=group["group_chat_messages_sent"],
                ordinary_messages_sent=group["ordinary_messages_sent"],
                service_events_attributed=group["service_events_attributed"],
            )
        )
    if friend_status is not None:
        contacts = [
            contact
            for contact in contacts
            if friend_status in contact.friend_statuses
        ]
    contacts.sort(
        key=lambda contact: (
            (contact.display_name or "").casefold(),
            contact.platforms,
            contact.platform_user_ids,
            contact.source_account_ids,
        )
    )
    contact_sort_value = {
        "total_messages_sent": lambda contact: contact.total_messages_sent,
        "personal_chat_messages_sent": lambda contact: (
            contact.personal_chat_messages_sent
        ),
        "group_chat_messages_sent": lambda contact: (
            contact.group_chat_messages_sent
        ),
    }[sort_by]
    contacts.sort(
        key=contact_sort_value,
        reverse=sort_direction == "desc",
    )
    options_contacts = contacts
    if platform:
        contacts = [
            contact
            for contact in contacts
            if platform in contact.platforms
            and (
                (contact.display_name and contact.display_name.strip())
                or contact.platform_user_ids
            )
        ]
    offset = (page - 1) * page_size
    return PaginatedItems(
        items=contacts[offset : offset + page_size],
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=len(contacts),
        ),
        options=[
            SearchOption(
                value=str(index),
                label=(contact.display_name or "").strip() or "Unnamed contact",
                platforms=contact.platforms,
                search_terms=[
                    *contact.platform_user_ids,
                    *contact.source_account_labels,
                ],
            )
            for index, contact in enumerate(options_contacts)
            if (contact.display_name and contact.display_name.strip())
            or contact.platform_user_ids
        ],
    )
