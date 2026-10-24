
from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.db import get_db
from app.models import Account, CanonicalIdentity, Chat, Contact, Message
from app.platforms import TELEGRAM_PLATFORM_ID
from app.schemas.analytics import (
    ChatStatistics,
    ContactStatistics,
    OverviewStatistics,
)

from .analytics_constants import (
    ORDINARY_MESSAGE_TYPE,
    SERVICE_MESSAGE_TYPE,
)

router = APIRouter()


@router.get(
    "/overview",
    response_model=OverviewStatistics,
    summary="Get communication overview",
    description=(
        "Counts account, chat, and message rows from Telegram imports only. "
        "Instagram records are excluded until cross-platform analysis is "
        "defined. Ordinary messages are rows "
        "with message_type='message'; service events are rows with "
        "message_type='service'. Other stored types contribute only to total "
        "messages. Timestamp bounds ignore messages with a null date."
    ),
)
def get_overview(db: Session = Depends(get_db)) -> OverviewStatistics:
    result = db.execute(
        select(
            select(func.count(Account.id))
            .where(Account.platform == TELEGRAM_PLATFORM_ID)
            .scalar_subquery()
            .label("total_imported_accounts"),
            select(func.count(Chat.id))
            .where(Chat.platform == TELEGRAM_PLATFORM_ID)
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
        .where(Message.platform == TELEGRAM_PLATFORM_ID)
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
            Chat.account_id,
            Account.username.label("account_username"),
            Account.name.label("account_name"),
            Chat.chat_id.label("telegram_chat_id"),
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
                Message.platform == TELEGRAM_PLATFORM_ID,
            ),
        )
        .group_by(
            Chat.id,
            Chat.account_id,
            Account.username,
            Account.name,
            Chat.chat_id,
            Chat.title,
            Chat.chat_type,
        )
        .where(
            Chat.platform == TELEGRAM_PLATFORM_ID,
            Account.platform == TELEGRAM_PLATFORM_ID,
        )
        .order_by(Chat.id)
    )
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
    return chats


@router.get(
    "/contacts",
    response_model=list[ContactStatistics],
    summary="Get communication statistics by sender/contact",
    description=(
        "Lists imported contacts and incoming senders for each platform. "
        "Within a platform, matching canonical identities are combined across "
        "source accounts; different platforms remain separate until explicit "
        "identity linking is used by future analytics. Unknown senders remain "
        "account-local. Contacts without messages are included with zero "
        "counts. Outgoing messages are excluded when direction or owner IDs "
        "identify them. Counts include all message types, with ordinary and "
        "service counts reported separately."
    ),
)
def get_contact_statistics(db: Session = Depends(get_db)) -> list[ContactStatistics]:
    owner_account = aliased(Account)
    sender_id = Message.sender_id
    is_owner = (
        select(owner_account.id)
        .where(
            owner_account.platform == Account.platform,
            owner_account.platform_user_id == sender_id,
        )
        .exists()
    )
    statement = (
        select(
            Chat.account_id.label("account_id"),
            Account.platform.label("platform"),
            Account.username.label("account_username"),
            Account.name.label("account_name"),
            Contact.id.label("contact_id"),
            CanonicalIdentity.id.label("canonical_identity_id"),
            sender_id.label("platform_user_id"),
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
        .join(Account, Chat.account_id == Account.id)
        .outerjoin(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.platform == Message.platform,
                or_(
                    Contact.id == Message.sender_contact_id,
                    Contact.platform_user_id == sender_id,
                    and_(
                        Message.platform == TELEGRAM_PLATFORM_ID,
                        Contact.platform_user_id == sender_id,
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
            Message.platform == Account.platform,
            Message.is_outgoing.is_not(True),
            or_(
                sender_id.is_(None),
                ~is_owner,
            ),
        )
        .group_by(
            Chat.account_id,
            Account.platform,
            Contact.id,
            CanonicalIdentity.id,
            Account.username,
            Account.name,
            sender_id,
            Contact.display_name,
        )
        .order_by(
            Account.platform,
            Chat.account_id,
            Contact.display_name,
            sender_id,
        )
    )
    groups: dict[tuple[object, ...], dict[str, object]] = {}
    for row in db.execute(statement):
        if row.canonical_identity_id is not None:
            key = ("canonical", row.platform, row.canonical_identity_id)
        elif row.contact_id is not None:
            key = ("contact", row.platform, row.contact_id)
        else:
            key = (
                "source",
                row.platform,
                row.account_id,
                row.platform_user_id,
            )
        group = groups.setdefault(
            key,
            {
                "platform": row.platform,
                "canonical_identity_id": row.canonical_identity_id,
                "platform_user_id": row.platform_user_id,
                "display_names": set(),
                "source_account_ids": set(),
                "source_account_labels": set(),
                "source_contact_ids": set(),
                "total_messages_sent": 0,
                "ordinary_messages_sent": 0,
                "service_events_attributed": 0,
            },
        )
        group["source_account_ids"].add(row.account_id)
        group["source_account_labels"].add(
            f"@{row.account_username}" if row.account_username else row.account_name
        )
        if row.contact_id is not None:
            group["source_contact_ids"].add(row.contact_id)
        if row.display_name:
            group["display_names"].add(row.display_name)
        group["total_messages_sent"] += int(row.total_messages_sent)
        group["ordinary_messages_sent"] += int(row.ordinary_messages_sent)
        group["service_events_attributed"] += int(row.service_events_attributed)

    owner_ids_by_platform: dict[str, set[str]] = {}
    for platform, user_id in db.execute(
        select(Account.platform, Account.platform_user_id).where(
            Account.platform_user_id.is_not(None)
        )
    ):
        owner_ids_by_platform.setdefault(platform, set()).add(user_id)

    for contact, account in db.execute(
        select(Contact, Account)
        .join(Account, Account.id == Contact.account_id)
        .where(Contact.platform == Account.platform)
    ):
        if contact.platform_user_id in owner_ids_by_platform.get(
            contact.platform,
            set(),
        ):
            continue
        if contact.canonical_identity_id is not None:
            key = (
                "canonical",
                contact.platform,
                contact.canonical_identity_id,
            )
        else:
            key = ("contact", contact.platform, contact.id)
        group = groups.setdefault(
            key,
            {
                "platform": contact.platform,
                "canonical_identity_id": contact.canonical_identity_id,
                "platform_user_id": contact.platform_user_id,
                "display_names": set(),
                "source_account_ids": set(),
                "source_account_labels": set(),
                "source_contact_ids": set(),
                "total_messages_sent": 0,
                "ordinary_messages_sent": 0,
                "service_events_attributed": 0,
            },
        )
        group["source_account_ids"].add(account.id)
        group["source_account_labels"].add(
            f"@{account.username}" if account.username else account.name
        )
        group["source_contact_ids"].add(contact.id)
        if contact.display_name:
            group["display_names"].add(contact.display_name)

    contacts = []
    for group in groups.values():
        source_account_ids = sorted(group["source_account_ids"])
        source_contact_ids = sorted(group["source_contact_ids"])
        display_names = sorted(group["display_names"], key=str.casefold)
        contacts.append(
            ContactStatistics(
                platform=group["platform"],
                account_id=(
                    source_account_ids[0] if len(source_account_ids) == 1 else None
                ),
                contact_id=source_contact_ids[0] if source_contact_ids else None,
                canonical_identity_id=group["canonical_identity_id"],
                source_account_ids=source_account_ids,
                source_account_labels=sorted(group["source_account_labels"]),
                source_contact_ids=source_contact_ids,
                platform_user_id=group["platform_user_id"],
                display_name=display_names[0] if display_names else None,
                total_messages_sent=group["total_messages_sent"],
                ordinary_messages_sent=group["ordinary_messages_sent"],
                service_events_attributed=group["service_events_attributed"],
            )
        )
    contacts.sort(
        key=lambda contact: (
            (contact.display_name or "").casefold(),
            contact.platform,
            contact.platform_user_id or "",
            contact.source_account_ids,
        )
    )
    return contacts
