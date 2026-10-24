from datetime import datetime
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import CTE, Select

from app.models import Account, CanonicalIdentity, Chat, Contact, Message
from app.platforms import TELEGRAM_PLATFORM_ID

from .analytics_constants import ORDINARY_MESSAGE_TYPE


def _utc_month_expression(db: Session):
    if db.get_bind().dialect.name == "postgresql":
        return func.to_char(
            func.timezone("UTC", Message.message_date),
            "YYYY-MM",
        )
    return func.strftime("%Y-%m", Message.message_date)


def build_forgotten_contact_queries(
    db: Session,
    owner_ids: Select,
    recent_start: datetime,
    current_time: datetime,
) -> tuple[CTE, Select, Select]:
    peers_statement = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Message.sender_id.label("peer_telegram_user_id"),
        )
        .join(Message, Message.chat_id == Chat.id)
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == TELEGRAM_PLATFORM_ID,
            Account.platform == TELEGRAM_PLATFORM_ID,
            Message.platform == TELEGRAM_PLATFORM_ID,
            Chat.chat_type == "personal_chat",
            Account.platform_user_id.is_not(None),
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.sender_id.is_not(None),
            Message.sender_id.not_in(owner_ids),
        )
        .distinct()
    )
    peers = peers_statement.cte("forgotten_contact_peers")
    single_peer_chats = (
        select(peers.c.chat_id)
        .group_by(peers.c.chat_id)
        .having(func.count() == 1)
        .cte("forgotten_single_peer_chats")
    )
    eligible_pairs = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            func.coalesce(CanonicalIdentity.id, -Contact.id).label(
                "identity_group_id"
            ),
            case(
                (CanonicalIdentity.id.is_(None), Chat.account_id),
                else_=None,
            ).label("identity_source_account_id"),
            CanonicalIdentity.id.label("canonical_identity_id"),
            Contact.id.label("contact_id"),
            Contact.telegram_user_id.label("contact_telegram_user_id"),
            Contact.display_name.label("display_name"),
        )
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == TELEGRAM_PLATFORM_ID,
            Account.platform == TELEGRAM_PLATFORM_ID,
        )
        .join(peers, peers.c.chat_id == Chat.id)
        .join(single_peer_chats, single_peer_chats.c.chat_id == Chat.id)
        .join(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.platform == TELEGRAM_PLATFORM_ID,
                Contact.telegram_user_id == peers.c.peer_telegram_user_id,
            ),
        )
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
        .cte("forgotten_eligible_pairs")
    )

    ordinary_message = Message.message_type == ORDINARY_MESSAGE_TYPE
    owner_direction = Message.sender_id.in_(owner_ids)
    contact_direction = and_(
        Message.sender_id == eligible_pairs.c.contact_telegram_user_id,
        Message.is_outgoing.is_(False),
    )
    known_direction = or_(owner_direction, contact_direction)
    historical_message = and_(
        Message.message_date < recent_start,
        Message.message_date <= current_time,
    )
    recent_message = and_(
        Message.message_date >= recent_start,
        Message.message_date <= current_time,
    )
    dated_message = Message.message_date <= current_time
    utc_message_date = (
        func.date(func.timezone("UTC", Message.message_date))
        if db.get_bind().dialect.name == "postgresql"
        else func.date(Message.message_date)
    )
    text_length = func.length(func.coalesce(Message.text_content, ""))

    def count_when(condition):
        return func.coalesce(
            func.sum(case((condition, 1), else_=0)),
            0,
        )

    aggregate_statement = (
        select(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            func.min(eligible_pairs.c.contact_id).label("contact_id"),
            func.min(eligible_pairs.c.canonical_identity_id).label(
                "canonical_identity_id"
            ),
            eligible_pairs.c.contact_telegram_user_id.label("telegram_user_id"),
            func.min(eligible_pairs.c.display_name).label("display_name"),
            count_when(and_(ordinary_message, owner_direction)).label(
                "owner_message_count"
            ),
            count_when(and_(ordinary_message, contact_direction)).label(
                "contact_message_count"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (and_(ordinary_message, owner_direction), text_length),
                        else_=0,
                    )
                ),
                0,
            ).label("owner_text_length"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(ordinary_message, contact_direction), text_length),
                        else_=0,
                    )
                ),
                0,
            ).label("contact_text_length"),
            func.count(
                case((and_(ordinary_message, known_direction), Message.id))
            ).label("known_message_count"),
            func.count(case((ordinary_message, Message.id))).label(
                "ordinary_message_count"
            ),
            func.min(
                case(
                    (and_(ordinary_message, known_direction, dated_message), Message.message_date)
                )
            ).label("first_message_at"),
            func.max(
                case(
                    (and_(ordinary_message, known_direction, dated_message), Message.message_date)
                )
            ).label("last_message_at"),
            func.count(
                func.distinct(
                    case(
                        (
                            and_(ordinary_message, known_direction, dated_message),
                            utc_message_date,
                        )
                    )
                )
            ).label("distinct_active_days"),
            count_when(
                and_(ordinary_message, known_direction, historical_message)
            ).label("historical_message_count"),
            func.min(
                case(
                    (
                        and_(ordinary_message, known_direction, historical_message),
                        Message.message_date,
                    )
                )
            ).label("historical_first_message_at"),
            func.max(
                case(
                    (
                        and_(ordinary_message, known_direction, historical_message),
                        Message.message_date,
                    )
                )
            ).label("historical_last_message_at"),
            func.count(
                func.distinct(
                    case(
                        (
                            and_(
                                ordinary_message,
                                known_direction,
                                historical_message,
                            ),
                            utc_message_date,
                        )
                    )
                )
            ).label("historical_active_days"),
            count_when(and_(ordinary_message, owner_direction, recent_message)).label(
                "recent_owner_message_count"
            ),
            count_when(
                and_(ordinary_message, contact_direction, recent_message)
            ).label("recent_contact_message_count"),
        )
        .select_from(eligible_pairs)
        .join(Message, Message.chat_id == eligible_pairs.c.chat_id)
        .where(Message.platform == TELEGRAM_PLATFORM_ID)
        .group_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            eligible_pairs.c.contact_telegram_user_id,
        )
    )

    month_expression = _utc_month_expression(db)
    historical_month = and_(
        ordinary_message,
        known_direction,
        historical_message,
    )
    recent_month = and_(
        ordinary_message,
        known_direction,
        recent_message,
    )
    monthly_statement = (
        select(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            month_expression.label("month"),
            count_when(and_(historical_month, owner_direction)).label(
                "historical_owner_message_count"
            ),
            count_when(and_(historical_month, contact_direction)).label(
                "historical_contact_message_count"
            ),
            count_when(and_(recent_month, owner_direction)).label(
                "recent_owner_message_count"
            ),
            count_when(and_(recent_month, contact_direction)).label(
                "recent_contact_message_count"
            ),
        )
        .select_from(eligible_pairs)
        .join(Message, Message.chat_id == eligible_pairs.c.chat_id)
        .where(
            Message.platform == TELEGRAM_PLATFORM_ID,
            Message.message_date.is_not(None),
            dated_message,
        )
        .group_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            month_expression,
        )
        .order_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            month_expression,
        )
    )
    return eligible_pairs, aggregate_statement, monthly_statement
