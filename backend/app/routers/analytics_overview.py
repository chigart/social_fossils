
from typing import Annotated, Literal, TypedDict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.constants import DEFAULT_PAGE_SIZE
from app.db import get_db
from app.models import Account, CanonicalIdentity, Chat, Contact, Message
from app.schemas.analytics import (
    ChatStatistics,
    ContactAccountSource,
    ContactStatistics,
    ImportedAccountStatistics,
    OverviewStatistics,
    PaginatedItems,
    PaginationMetadata,
    SearchOption,
)

from .analytics_constants import (
    ORDINARY_MESSAGE_TYPE,
    SERVICE_MESSAGE_TYPE,
)

router = APIRouter()


class ContactGroup(TypedDict):
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
    ordinary_messages_sent: int
    service_events_attributed: int


@router.get(
    "/overview",
    response_model=OverviewStatistics,
    summary="Get communication overview",
    description=(
        "Counts normalized account, chat, and message rows across imported "
        "platforms. Ordinary messages are rows "
        "with message_type='message'; service events are rows with "
        "message_type='service'. Other stored types contribute only to total "
        "messages. Timestamp bounds ignore messages with a null date."
    ),
)
def get_overview(db: Session = Depends(get_db)) -> OverviewStatistics:
    result = db.execute(
        select(
            select(func.count(Account.id))
            .scalar_subquery()
            .label("total_imported_accounts"),
            select(func.count(Chat.id))
            .scalar_subquery()
            .label("total_chats"),
            func.count(Message.id).label("total_messages"),
            func.count(
                case((Message.message_type == ORDINARY_MESSAGE_TYPE, Message.id))
            ).label("total_ordinary_messages"),
            func.count(
                case((Message.message_type == SERVICE_MESSAGE_TYPE, Message.id))
            ).label("total_service_messages"),
            func.min(Message.message_date).label("earliest_message_timestamp"),
            func.max(Message.message_date).label("latest_message_timestamp"),
        )
        .select_from(Message)
    ).one()

    imported_accounts = [
        ImportedAccountStatistics(
            id=row.id,
            platform=row.platform,
            name=row.name,
            username=row.username,
            platform_user_id=row.platform_user_id,
            total_messages=row.total_messages,
            total_contacts=row.total_contacts,
        )
        for row in db.execute(
            select(
                Account.id,
                Account.platform,
                Account.name,
                Account.username,
                Account.platform_user_id,
                (
                    select(func.count(Message.id))
                    .select_from(Message)
                    .join(Chat, Chat.id == Message.chat_id)
                    .where(Chat.account_id == Account.id)
                    .scalar_subquery()
                ).label("total_messages"),
                (
                    select(func.count(Contact.id))
                    .where(Contact.account_id == Account.id)
                    .scalar_subquery()
                ).label("total_contacts"),
            ).order_by(Account.id)
        )
    ]

    return OverviewStatistics(
        **result._mapping,
        imported_accounts=imported_accounts,
    )


@router.get(
    "/chats",
    response_model=PaginatedItems[ChatStatistics],
    summary="Get communication statistics by chat",
    description=(
        "Returns a page of chats, including chats with no messages. The response "
        "also includes the total row count and lightweight options for searching "
        "all chats. Counts include "
        "all stored message types; ordinary and service counts use the exact "
        "'message' and 'service' values. Distinct senders count non-null "
        "platform-scoped sender IDs as normalized and stored by the importer."
    ),
)
def get_chat_statistics(
    db: Session = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = DEFAULT_PAGE_SIZE,
    sort_by: Literal["title", "total_messages"] = "total_messages",
    sort_direction: Literal["asc", "desc"] = "desc",
) -> PaginatedItems[ChatStatistics]:
    statement = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id,
            Chat.platform,
            Account.username.label("account_username"),
            Account.name.label("account_name"),
            Chat.chat_id.label("platform_chat_id"),
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
            func.count(func.distinct(Message.sender_id)).label(
                "distinct_identified_senders"
            ),
        )
        .select_from(Chat)
        .join(Account, Account.id == Chat.account_id)
        .outerjoin(
            Message,
            and_(
                Message.chat_id == Chat.id,
                Message.platform == Chat.platform,
            ),
        )
        .group_by(
            Chat.id,
            Chat.account_id,
            Chat.platform,
            Account.username,
            Account.name,
            Chat.chat_id,
            Chat.title,
            Chat.chat_type,
        )
        .where(
            Chat.platform == Account.platform,
        )
    )
    primary_sort = (
        func.lower(func.coalesce(Chat.title, ""))
        if sort_by == "title"
        else func.count(Message.id)
    )
    primary_order = (
        primary_sort.asc()
        if sort_direction == "asc"
        else primary_sort.desc()
    )
    statement = statement.order_by(primary_order, Chat.id.asc()).offset(
        (page - 1) * page_size
    ).limit(page_size)
    chats = []
    for row in db.execute(statement):
        source_account_label = (
            f"@{row.account_username}" if row.account_username else row.account_name
        )
        chats.append(
            ChatStatistics(
                **{
                    key: value
                    for key, value in row._mapping.items()
                    if key not in {"account_username", "account_name"}
                },
                source_account_label=source_account_label,
            )
        )
    total = int(
        db.scalar(
            select(func.count(Chat.id))
            .join(Account, Account.id == Chat.account_id)
            .where(Chat.platform == Account.platform)
        )
        or 0
    )
    option_statement = (
        select(
            Chat.id,
            Chat.platform,
            Chat.chat_id.label("platform_chat_id"),
            Chat.title,
            Chat.chat_type,
            Account.username,
            Account.name,
            func.count(Message.id).label("total_messages"),
        )
        .join(Account, Account.id == Chat.account_id)
        .outerjoin(
            Message,
            and_(
                Message.chat_id == Chat.id,
                Message.platform == Chat.platform,
            ),
        )
        .where(Chat.platform == Account.platform)
        .group_by(
            Chat.id,
            Chat.platform,
            Chat.chat_id,
            Chat.title,
            Chat.chat_type,
            Account.username,
            Account.name,
        )
        .order_by(primary_order, Chat.id.asc())
    )
    return PaginatedItems(
        items=chats,
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=total,
        ),
        options=[
            SearchOption(
                value=str(row.id),
                label=row.title or "Untitled chat",
                platforms=[row.platform],
                search_terms=[
                    row.platform_chat_id,
                    row.chat_type,
                    f"@{row.username}" if row.username else row.name,
                ],
            )
            for row in db.execute(option_statement)
        ],
    )


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
        "separately."
    ),
)
def get_contact_statistics(
    db: Session = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = DEFAULT_PAGE_SIZE,
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

    def contact_key(
        platform: str,
        account_id: int,
        contact_id: int | None,
        identity_id: int | None,
        identity_group_id: int | None,
        platform_user_id: str | None,
    ) -> tuple[object, ...]:
        if identity_group_id is not None:
            return ("group", identity_group_id)
        if identity_id is not None:
            return ("identity", identity_id)
        if contact_id is not None:
            return ("contact", contact_id)
        return ("source", platform, account_id, platform_user_id)

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
                "identity_ids": set(),
                "identity_group_id": identity_group_id,
                "platform_user_ids": set(),
                "display_names": set(),
                "source_account_ids": set(),
                "source_account_labels": set(),
                "source_accounts": set(),
                "source_contact_ids": set(),
                "total_messages_sent": 0,
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
        key = contact_key(
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
        group["ordinary_messages_sent"] += int(row.ordinary_messages_sent)
        group["service_events_attributed"] += int(row.service_events_attributed)

    owner_ids_by_platform: dict[str, set[str]] = {}
    for platform, user_id in db.execute(
        select(Account.platform, Account.platform_user_id).where(
            Account.platform_user_id.is_not(None)
        )
    ):
        if user_id is not None:
            owner_ids_by_platform.setdefault(platform, set()).add(user_id)

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
        key = contact_key(
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

    contacts = []
    for group in groups.values():
        source_account_ids = sorted(group["source_account_ids"])
        source_contact_ids = sorted(group["source_contact_ids"])
        display_names = sorted(group["display_names"], key=str.casefold)
        contacts.append(
            ContactStatistics(
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
                ordinary_messages_sent=group["ordinary_messages_sent"],
                service_events_attributed=group["service_events_attributed"],
            )
        )
    contacts.sort(
        key=lambda contact: (
            (contact.display_name or "").casefold(),
            contact.platforms,
            contact.platform_user_ids,
            contact.source_account_ids,
        )
    )
    contacts.sort(
        key=lambda contact: contact.total_messages_sent,
        reverse=sort_direction == "desc",
    )
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
                label=contact.display_name or "Unnamed contact",
                platforms=contact.platforms,
                search_terms=[
                    *contact.platform_user_ids,
                    *contact.source_account_labels,
                ],
            )
            for index, contact in enumerate(contacts)
        ],
    )
