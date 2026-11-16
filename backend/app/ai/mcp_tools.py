from typing import Annotated, Literal

from mcp.server import MCPServer
from pydantic import Field
from sqlalchemy import and_, case, func, select

from app.constants import ORDINARY_MESSAGE_TYPE
from app.db import SessionLocal
from app.models import Chat, Message
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
) -> dict[str, int | str | None]:
    """Return aggregate metrics for one selected chat without names or message text."""
    with SessionLocal() as db:
        row = db.execute(
            select(
                Chat.id.label("chat_id"),
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
            .outerjoin(
                Message,
                and_(
                    Message.chat_id == Chat.id,
                    Message.platform == Chat.platform,
                ),
            )
            .where(Chat.id == chat_id)
            .group_by(Chat.id)
        ).one_or_none()
    if row is None:
        raise ValueError("No eligible analytics were found for the selected chat.")

    return {
        "chat_id": row.chat_id,
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
    }


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
