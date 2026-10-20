from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.db import get_db
from app.models import Chat, Contact, Message, TelegramAccount
from app.schemas.analytics import (
    ChatStatistics,
    ContactStatistics,
    OverviewStatistics,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

ORDINARY_MESSAGE_TYPE = "message"
SERVICE_MESSAGE_TYPE = "service"


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