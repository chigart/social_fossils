from typing import Annotated, Literal

from mcp.server import MCPServer
from pydantic import Field
from sqlalchemy import and_, case, func, or_, select

from app.constants import ORDINARY_MESSAGE_TYPE
from app.db import SessionLocal
from app.models import Account, Chat, Contact, Message
from app.routers.analytics_communication_balance import get_communication_balance
from app.routers.analytics_forgotten_contacts import (
    build_forgotten_contacts_statistics,
)
from app.routers.analytics_overview import (
    get_chat_statistics,
    get_overview,
)

mcp_server = MCPServer("Social Fossils analytics")


@mcp_server.tool()
def list_accounts(
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> list[dict[str, int | str | None]]:
    """List imported accounts by platform, account name, and account username."""
    with SessionLocal() as db:
        rows = db.execute(
            select(
                Account.id,
                Account.platform,
                Account.name,
                Account.username,
            )
            .order_by(Account.platform, Account.name, Account.id)
            .limit(limit)
        )
        return [
            {
                "account_id": row.id,
                "platform": row.platform,
                "account_name": row.name,
                "username": row.username,
            }
            for row in rows
        ]


@mcp_server.tool()
def search_users(
    query: Annotated[str, Field(min_length=1, max_length=100)],
    platform: Literal["facebook", "instagram", "telegram", "vk"] | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
) -> list[dict[str, int | str | None]]:
    """Search contact display names and usernames; never returns message content."""
    search_term = query.strip().casefold()
    if not search_term:
        raise ValueError("Search query must contain at least one non-space character.")

    name_matches = func.lower(Contact.display_name).contains(
        search_term,
        autoescape=True,
        escape="\\",
    )
    username_matches = func.lower(Contact.username).contains(
        search_term,
        autoescape=True,
        escape="\\",
    )
    statement = (
        select(
            Contact.id.label("contact_id"),
            Contact.account_id,
            Contact.platform,
            Contact.display_name,
            Contact.username,
            Account.name.label("account_name"),
            Account.username.label("account_username"),
        )
        .join(Account, Account.id == Contact.account_id)
        .where(
            Contact.platform == Account.platform,
            or_(name_matches, username_matches),
        )
        .order_by(
            Contact.platform,
            Contact.display_name,
            Contact.username,
            Contact.id,
        )
        .limit(limit)
    )
    if platform is not None:
        statement = statement.where(Contact.platform == platform)

    with SessionLocal() as db:
        rows = db.execute(statement)
        return [
            {
                "contact_id": row.contact_id,
                "account_id": row.account_id,
                "platform": row.platform,
                "display_name": row.display_name,
                "username": row.username,
                "account_name": row.account_name,
                "account_username": row.account_username,
            }
            for row in rows
        ]


@mcp_server.tool()
def get_overview_summary() -> dict[str, int | str | None]:
    """Return aggregate account, chat, message, and date-range statistics."""
    with SessionLocal() as db:
        overview = get_overview(db)
    return {
        "total_imported_accounts": overview.total_imported_accounts,
        "total_chats": overview.total_chats,
        "total_messages": overview.total_messages,
        "total_ordinary_messages": overview.total_ordinary_messages,
        "total_service_messages": overview.total_service_messages,
        "earliest_message_timestamp": (
            overview.earliest_message_timestamp.isoformat()
            if overview.earliest_message_timestamp
            else None
        ),
        "latest_message_timestamp": (
            overview.latest_message_timestamp.isoformat()
            if overview.latest_message_timestamp
            else None
        ),
    }


@mcp_server.tool()
def get_top_chat_metrics(
    limit: Annotated[int, Field(ge=1, le=20)] = 10,
    scope: Literal["all", "dm", "group"] = "all",
    platform: Literal["facebook", "instagram", "telegram", "vk"] | None = None,
) -> list[dict[str, int | str | None]]:
    """Return top chat counts and date ranges, optionally filtered by platform."""
    with SessionLocal() as db:
        chats = get_chat_statistics(
            db,
            page=1,
            page_size=limit,
            sort_by="total_messages",
            sort_direction="desc",
            chat_scope=scope,
            platform=platform,
        )
    return [
        {
            "chat_id": chat.chat_id,
            "platform": chat.platform,
            "chat_type": chat.chat_type,
            "total_messages": chat.total_messages,
            "ordinary_messages": chat.ordinary_messages,
            "earliest_message_timestamp": (
                chat.earliest_message_timestamp.isoformat()
                if chat.earliest_message_timestamp
                else None
            ),
            "latest_message_timestamp": (
                chat.latest_message_timestamp.isoformat()
                if chat.latest_message_timestamp
                else None
            ),
        }
        for chat in chats.items
    ]


@mcp_server.tool()
def get_selected_chat_metrics(
    chat_id: Annotated[int, Field(gt=0)],
) -> dict[str, int | str | None | list[dict[str, int | str | None]]]:
    """Return selected-chat metrics, account and participant names, but no message text."""
    with SessionLocal() as db:
        row = db.execute(
            select(
                Chat.id.label("chat_id"),
                Chat.title.label("chat_title"),
                Account.name.label("account_name"),
                Account.username.label("account_username"),
                func.count(Message.id).label("total_messages"),
                func.count(
                    case(
                        (Message.message_type == ORDINARY_MESSAGE_TYPE, Message.id)
                    )
                ).label("total_ordinary_messages"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Message.message_type == ORDINARY_MESSAGE_TYPE,
                                func.length(func.coalesce(Message.text_content, "")),
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_text_length"),
                func.min(Message.message_date).label("earliest_message_timestamp"),
                func.max(Message.message_date).label("latest_message_timestamp"),
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
            .where(Chat.id == chat_id)
            .group_by(Chat.id, Account.id)
        ).one_or_none()
        participants = db.execute(
            select(
                Contact.id.label("contact_id"),
                Contact.display_name,
                Contact.username,
                Message.sender_name,
            )
            .select_from(Message)
            .join(Chat, Chat.id == Message.chat_id)
            .outerjoin(Contact, Contact.id == Message.sender_contact_id)
            .where(
                Chat.id == chat_id,
                Message.platform == Chat.platform,
                or_(
                    Contact.display_name.is_not(None),
                    Contact.username.is_not(None),
                    Message.sender_name.is_not(None),
                ),
            )
            .distinct()
            .order_by(
                Contact.display_name,
                Contact.username,
                Message.sender_name,
            )
            .limit(50)
        )
    if row is None:
        raise ValueError("No eligible analytics were found for the selected chat.")

    return {
        "chat_id": row.chat_id,
        "chat_title": row.chat_title,
        "account_name": row.account_name,
        "account_username": row.account_username,
        "total_messages": row.total_messages,
        "total_ordinary_messages": row.total_ordinary_messages,
        "total_text_length": row.total_text_length,
        "earliest_message_timestamp": (
            row.earliest_message_timestamp.isoformat()
            if row.earliest_message_timestamp
            else None
        ),
        "latest_message_timestamp": (
            row.latest_message_timestamp.isoformat()
            if row.latest_message_timestamp
            else None
        ),
        "participants": [
            {
                "contact_id": participant.contact_id,
                "display_name": (
                    participant.display_name or participant.sender_name
                ),
                "username": participant.username,
            }
            for participant in participants
        ],
    }


@mcp_server.tool()
def get_chat_messages(
    chat_id: Annotated[int, Field(gt=0)],
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> list[dict[str, str | bool | None]]:
    """Return recent ordinary message text for a chat. Available only to local Ollama."""
    with SessionLocal() as db:
        rows = db.execute(
            select(
                Message.id,
                Message.message_date,
                Message.is_outgoing,
                Message.sender_name,
                Contact.display_name,
                Message.text_content,
            )
            .join(Chat, Chat.id == Message.chat_id)
            .outerjoin(Contact, Contact.id == Message.sender_contact_id)
            .where(
                Chat.id == chat_id,
                Message.platform == Chat.platform,
                Message.message_type == ORDINARY_MESSAGE_TYPE,
                Message.text_content.is_not(None),
                Message.text_content != "",
            )
            .order_by(Message.message_date.desc(), Message.id.desc())
            .limit(limit)
        ).all()

    return [
        {
            "timestamp": row.message_date.isoformat() if row.message_date else None,
            "is_outgoing": row.is_outgoing,
            "sender": row.display_name or row.sender_name,
            "text": row.text_content,
        }
        for row in reversed(rows)
    ]


@mcp_server.tool()
def get_communication_balance_summary(
    platform: Literal["facebook", "instagram", "telegram", "vk"] | None = None,
) -> dict[str, int]:
    """Return aggregate communication-balance counts, optionally by platform."""
    with SessionLocal() as db:
        balance = get_communication_balance(
            db,
            sort_by="text_volume",
            sort_direction="desc",
            classification=None,
            page=1,
            page_size=1,
            platform=platform,
        )
    return balance.summary.model_dump()


@mcp_server.tool()
def get_forgotten_contact_summary(
    scope: Literal["private", "group"] = "private",
    platform: Literal["facebook", "instagram", "telegram", "vk"] | None = None,
) -> dict[str, int | str]:
    """Return aggregate forgotten-contact counts, optionally by platform."""
    with SessionLocal() as db:
        statistics = build_forgotten_contacts_statistics(
            db,
            scope=scope,
            limit=1,
            offset=0,
            platform=platform,
        )
    return statistics.summary.model_dump()
