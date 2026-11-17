from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select

from app.constants import CONVERSATION_GAP, ORDINARY_MESSAGE_TYPE
from app.models import Chat, Message


def build_reply_turns_statement(
    db: Session,
    *,
    response_is_outgoing: bool,
) -> Select:
    message = aliased(Message)
    order_by = (message.message_date, message.id)
    previous_message_date = func.lag(message.message_date).over(
        partition_by=message.chat_id,
        order_by=order_by,
    )
    dated_messages = (
        select(
            message.chat_id.label("chat_id"),
            message.id.label("message_id"),
            message.message_date.label("message_date"),
            message.is_outgoing.label("is_outgoing"),
            message.sender_id.label("sender_id"),
            previous_message_date.label("previous_message_date"),
        )
        .select_from(message)
        .join(
            Chat,
            and_(
                Chat.id == message.chat_id,
                Chat.platform == message.platform,
                Chat.chat_type == "personal_chat",
            ),
        )
        .where(
            message.message_type == ORDINARY_MESSAGE_TYPE,
            message.message_date.is_not(None),
        )
        .subquery()
    )
    gap_seconds = (
        (func.julianday(dated_messages.c.message_date)
         - func.julianday(dated_messages.c.previous_message_date))
        * 86400
        if db.get_bind().dialect.name == "sqlite"
        else func.extract(
            "epoch",
            dated_messages.c.message_date - dated_messages.c.previous_message_date,
        )
    )
    session_starts = (
        select(
            dated_messages.c.chat_id,
            dated_messages.c.message_id,
            dated_messages.c.message_date,
            dated_messages.c.is_outgoing,
            dated_messages.c.sender_id,
            case(
                (
                    dated_messages.c.previous_message_date.is_(None)
                    | (gap_seconds >= CONVERSATION_GAP.total_seconds()),
                    1,
                ),
                else_=0,
            ).label("starts_session"),
        )
        .subquery()
    )
    session_number = func.sum(session_starts.c.starts_session).over(
        partition_by=session_starts.c.chat_id,
        order_by=(session_starts.c.message_date, session_starts.c.message_id),
        rows=(None, 0),
    )
    sessioned_messages = (
        select(
            session_starts.c.chat_id,
            session_starts.c.message_id,
            session_starts.c.message_date,
            session_starts.c.is_outgoing,
            session_starts.c.sender_id,
            session_number.label("session_number"),
        )
        .subquery()
    )
    session_partition = (
        sessioned_messages.c.chat_id,
        sessioned_messages.c.session_number,
    )
    first_message_date = func.first_value(
        sessioned_messages.c.message_date
    ).over(
        partition_by=session_partition,
        order_by=(
            sessioned_messages.c.message_date,
            sessioned_messages.c.message_id,
        ),
    )
    first_message_outgoing = func.first_value(
        sessioned_messages.c.is_outgoing
    ).over(
        partition_by=session_partition,
        order_by=(
            sessioned_messages.c.message_date,
            sessioned_messages.c.message_id,
        ),
    )
    first_message_sender_id = func.first_value(
        sessioned_messages.c.sender_id
    ).over(
        partition_by=session_partition,
        order_by=(
            sessioned_messages.c.message_date,
            sessioned_messages.c.message_id,
        ),
    )
    first_response_date = func.min(
        case(
            (
                sessioned_messages.c.is_outgoing.is_(response_is_outgoing),
                sessioned_messages.c.message_date,
            ),
            else_=None,
        )
    ).over(partition_by=session_partition)
    session_messages = (
        select(
            sessioned_messages.c.chat_id,
            sessioned_messages.c.session_number,
            first_message_date.label("first_message_date"),
            first_message_outgoing.label("first_message_outgoing"),
            first_message_sender_id.label("first_message_sender_id"),
            first_response_date.label("first_response_date"),
        )
        .subquery()
    )
    elapsed_seconds = (
        (func.julianday(session_messages.c.first_response_date)
         - func.julianday(session_messages.c.first_message_date))
        * 86400
        if db.get_bind().dialect.name == "sqlite"
        else func.extract(
            "epoch",
            session_messages.c.first_response_date
            - session_messages.c.first_message_date,
        )
    )
    return (
        select(
            session_messages.c.chat_id,
            session_messages.c.first_response_date.label("message_date"),
            elapsed_seconds.label("elapsed_seconds"),
        )
        .distinct()
        .where(
            session_messages.c.first_message_outgoing.is_(
                not response_is_outgoing
            ),
            session_messages.c.first_message_sender_id.is_not(None),
            session_messages.c.first_response_date.is_not(None),
            elapsed_seconds >= 0,
            elapsed_seconds < CONVERSATION_GAP.total_seconds(),
        )
    )
