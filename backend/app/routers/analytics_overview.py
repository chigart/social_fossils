
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.constants import DEFAULT_PAGE_SIZE, ORDINARY_MESSAGE_TYPE, SERVICE_MESSAGE_TYPE
from app.db import get_db
from app.models import Account, Chat, Contact, Message
from app.schemas.analytics import (
    ChatStatistics,
    ImportedAccountStatistics,
    OverviewStatistics,
    PaginatedItems,
    PaginationMetadata,
    SearchOption,
)

router = APIRouter()


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
            total_text_length=row.total_text_length,
            total_contacts=row.total_contacts,
            earliest_message_timestamp=row.earliest_message_timestamp,
            latest_message_timestamp=row.latest_message_timestamp,
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
                    select(
                        func.coalesce(
                            func.sum(
                                func.length(
                                    func.coalesce(Message.text_content, "")
                                )
                            ),
                            0,
                        )
                    )
                    .select_from(Message)
                    .join(Chat, Chat.id == Message.chat_id)
                    .where(
                        Chat.account_id == Account.id,
                        Message.message_type == ORDINARY_MESSAGE_TYPE,
                    )
                    .scalar_subquery()
                ).label("total_text_length"),
                (
                    select(func.min(Message.message_date))
                    .select_from(Message)
                    .join(Chat, Chat.id == Message.chat_id)
                    .where(Chat.account_id == Account.id)
                    .scalar_subquery()
                ).label("earliest_message_timestamp"),
                (
                    select(func.max(Message.message_date))
                    .select_from(Message)
                    .join(Chat, Chat.id == Message.chat_id)
                    .where(Chat.account_id == Account.id)
                    .scalar_subquery()
                ).label("latest_message_timestamp"),
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
        "Returns a page of chats, including chats with no messages. The optional "
        "chat_scope filter selects 'dm' (chat_type='personal_chat'), 'group' "
        "(any other chat type), or 'all'; the optional platform filter limits "
        "results and pagination to that platform. The response "
        "also includes the total row count and lightweight options for searching "
        "the selected scope. DM rows include average response time for measured "
        "in-chat replies. Counts include "
        "all stored message types; ordinary and service counts use the exact "
        "'message' and 'service' values. Distinct senders count non-null "
        "platform-scoped sender IDs as normalized and stored by the importer."
    ),
)
def get_chat_statistics(
    db: Session = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = DEFAULT_PAGE_SIZE,
    sort_by: Literal[
        "title",
        "total_messages",
        "text_length",
        "average_response_seconds",
        "distinct_identified_senders",
        "earliest_message_timestamp",
        "latest_message_timestamp",
    ] = "total_messages",
    sort_direction: Literal["asc", "desc"] = "desc",
    chat_scope: Literal["dm", "group", "all"] = "all",
    platform: str | None = None,
) -> PaginatedItems[ChatStatistics]:
    chat_scope_filter = (
        Chat.chat_type == "personal_chat"
        if chat_scope == "dm"
        else Chat.chat_type != "personal_chat"
        if chat_scope == "group"
        else None
    )
    chat_filters = [
        Chat.platform == Account.platform,
    ]
    if chat_scope_filter is not None:
        chat_filters.append(chat_scope_filter)
    if platform:
        chat_filters.append(Chat.platform == platform)
    option_filters = [Chat.platform == Account.platform]
    if chat_scope_filter is not None:
        option_filters.append(chat_scope_filter)
    text_length = func.coalesce(
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
    )
    reply_average = None
    if chat_scope == "dm":
        reply_message = aliased(Message)
        original_message = aliased(Message)
        reply_elapsed_seconds = (
            (func.julianday(reply_message.message_date)
             - func.julianday(original_message.message_date))
            * 86400
            if db.get_bind().dialect.name == "sqlite"
            else func.extract(
                "epoch",
                reply_message.message_date - original_message.message_date,
            )
        )
        average_response_seconds = func.avg(reply_elapsed_seconds)
        if db.get_bind().dialect.name == "sqlite":
            average_response_seconds = func.round(average_response_seconds, 3)
        reply_average = (
            select(
                reply_message.chat_id.label("chat_id"),
                average_response_seconds.label("average_response_seconds"),
            )
            .join(
                original_message,
                and_(
                    original_message.chat_id == reply_message.chat_id,
                    original_message.platform == reply_message.platform,
                    original_message.message_id
                    == func.coalesce(
                        reply_message.source_reply_id,
                        reply_message.reply_to_telegram_message_id,
                    ),
                    original_message.message_type == ORDINARY_MESSAGE_TYPE,
                ),
            )
            .where(
                reply_message.message_type == ORDINARY_MESSAGE_TYPE,
                reply_message.sender_id.is_not(None),
                original_message.sender_id.is_not(None),
                reply_message.sender_id != original_message.sender_id,
                reply_message.message_date.is_not(None),
                original_message.message_date.is_not(None),
                reply_elapsed_seconds >= 0,
            )
            .group_by(reply_message.chat_id)
            .subquery()
        )

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
            text_length.label("text_length"),
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
            *chat_filters,
        )
    )
    if reply_average is not None:
        statement = statement.outerjoin(
            reply_average,
            reply_average.c.chat_id == Chat.id,
        ).group_by(
            reply_average.c.average_response_seconds,
        ).add_columns(
            reply_average.c.average_response_seconds.label(
                "average_response_seconds"
            )
        )
    primary_sort = {
        "title": func.lower(func.coalesce(Chat.title, "")),
        "total_messages": func.count(Message.id),
        "text_length": text_length,
        "average_response_seconds": (
            reply_average.c.average_response_seconds
            if reply_average is not None
            else Chat.id
        ),
        "distinct_identified_senders": func.count(
            func.distinct(Message.sender_id)
        ),
        "earliest_message_timestamp": func.min(Message.message_date),
        "latest_message_timestamp": func.max(Message.message_date),
    }[sort_by]
    primary_order = (
        primary_sort.asc().nulls_last()
        if sort_direction == "asc"
        else primary_sort.desc().nulls_last()
    )
    statement = statement.order_by(primary_order, Chat.id.asc()).offset(
        (page - 1) * page_size
    ).limit(page_size)
    chat_rows = list(db.execute(statement))
    chats = []
    for row in chat_rows:
        source_account_label = (
            f"@{row.account_username}" if row.account_username else row.account_name
        )
        chats.append(
            ChatStatistics(
                **{
                    key: value
                    for key, value in row._mapping.items()
                    if key not in {
                        "account_username",
                        "account_name",
                        "average_response_seconds",
                    }
                },
                source_account_label=source_account_label,
                average_response_seconds=row._mapping.get("average_response_seconds"),
            )
        )
    total = int(
        db.scalar(
            select(func.count(Chat.id))
            .join(Account, Account.id == Chat.account_id)
            .where(*chat_filters)
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
        .where(*option_filters)
        .group_by(
            Chat.id,
            Chat.platform,
            Chat.chat_id,
            Chat.title,
            Chat.chat_type,
            Account.username,
            Account.name,
        )
    )
    if reply_average is not None:
        option_statement = option_statement.outerjoin(
            reply_average,
            reply_average.c.chat_id == Chat.id,
        ).group_by(
            reply_average.c.average_response_seconds,
        )
    option_statement = option_statement.order_by(primary_order, Chat.id.asc())
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
