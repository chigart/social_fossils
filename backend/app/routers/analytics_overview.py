
from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CanonicalIdentity, Chat, Contact, Message, TelegramAccount
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
            Chat.account_id,
            TelegramAccount.username.label("account_username"),
            TelegramAccount.name.label("account_name"),
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
        .join(TelegramAccount, TelegramAccount.id == Chat.account_id)
        .outerjoin(Message, Message.chat_id == Chat.id)
        .group_by(
            Chat.id,
            Chat.account_id,
            TelegramAccount.username,
            TelegramAccount.name,
            Chat.telegram_chat_id,
            Chat.title,
            Chat.chat_type,
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
        "Groups incoming messages by canonical platform and normalized user "
        "ID, never by display name. Matching contacts and their counts are "
        "combined across source accounts. Sender IDs without a matching "
        "canonical identity and null sender IDs remain account-local. All "
        "imported owner IDs are aliases and outgoing messages are excluded. "
        "Counts include all message types, with ordinary and service counts "
        "reported separately."
    ),
)
def get_contact_statistics(db: Session = Depends(get_db)) -> list[ContactStatistics]:
    owner_ids = select(TelegramAccount.telegram_user_id).where(
        TelegramAccount.telegram_user_id.is_not(None)
    )
    statement = (
        select(
            Chat.account_id.label("account_id"),
            TelegramAccount.username.label("account_username"),
            TelegramAccount.name.label("account_name"),
            Contact.id.label("contact_id"),
            CanonicalIdentity.id.label("canonical_identity_id"),
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
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
        .where(
            Message.is_outgoing.is_not(True),
            or_(
                Message.sender_telegram_id.is_(None),
                Message.sender_telegram_id.not_in(owner_ids),
            ),
        )
        .group_by(
            Chat.account_id,
            Contact.id,
            CanonicalIdentity.id,
            TelegramAccount.username,
            TelegramAccount.name,
            Message.sender_telegram_id,
            Contact.display_name,
        )
        .order_by(Chat.account_id, Contact.display_name, Message.sender_telegram_id)
    )
    groups: dict[tuple[object, ...], dict[str, object]] = {}
    for row in db.execute(statement):
        if row.canonical_identity_id is not None:
            key = ("canonical", row.canonical_identity_id)
        else:
            key = ("source", row.account_id, row.telegram_user_id)
        group = groups.setdefault(
            key,
            {
                "canonical_identity_id": row.canonical_identity_id,
                "telegram_user_id": row.telegram_user_id,
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

    contacts = []
    for group in groups.values():
        source_account_ids = sorted(group["source_account_ids"])
        source_contact_ids = sorted(group["source_contact_ids"])
        display_names = sorted(group["display_names"], key=str.casefold)
        contacts.append(
            ContactStatistics(
                account_id=(
                    source_account_ids[0] if len(source_account_ids) == 1 else None
                ),
                contact_id=source_contact_ids[0] if source_contact_ids else None,
                canonical_identity_id=group["canonical_identity_id"],
                source_account_ids=source_account_ids,
                source_account_labels=sorted(group["source_account_labels"]),
                source_contact_ids=source_contact_ids,
                telegram_user_id=group["telegram_user_id"],
                display_name=display_names[0] if display_names else None,
                total_messages_sent=group["total_messages_sent"],
                ordinary_messages_sent=group["ordinary_messages_sent"],
                service_events_attributed=group["service_events_attributed"],
            )
        )
    contacts.sort(
        key=lambda contact: (
            (contact.display_name or "").casefold(),
            contact.telegram_user_id or "",
            contact.source_account_ids,
        )
    )
    return contacts
