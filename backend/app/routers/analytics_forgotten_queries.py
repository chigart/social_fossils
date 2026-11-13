from datetime import datetime
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.selectable import CTE, Select

from app.models import Account, CanonicalIdentity, Chat, Contact, Message

from app.constants import ORDINARY_MESSAGE_TYPE


def _utc_month_expression(db: Session):
    if db.get_bind().dialect.name == "postgresql":
        return func.to_char(
            func.timezone("UTC", Message.message_date),
            "YYYY-MM",
        )
    return func.strftime("%Y-%m", Message.message_date)


def build_forgotten_contact_queries(
    db: Session,
    recent_start: datetime,
    current_time: datetime,
) -> tuple[CTE, Select, Select]:
    owner_account = aliased(Account)
    owner_sender = (
        select(owner_account.id)
        .where(
            owner_account.platform == Message.platform,
            owner_account.platform_user_id == Message.sender_id,
        )
        .exists()
    )
    peers_statement = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id.label("account_id"),
            Message.sender_id.label("peer_platform_user_id"),
        )
        .join(Message, Message.chat_id == Chat.id)
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == Account.platform,
            Message.platform == Chat.platform,
            Chat.chat_type == "personal_chat",
            Account.platform_user_id.is_not(None),
            Message.message_type == ORDINARY_MESSAGE_TYPE,
            Message.sender_id.is_not(None),
            ~owner_sender,
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
            CanonicalIdentity.identity_group_id.label("identity_group_id"),
            case(
                (
                    CanonicalIdentity.identity_group_id.is_(None),
                    CanonicalIdentity.id,
                ),
                else_=None,
            ).label("canonical_identity_id"),
            case(
                (
                    and_(
                        CanonicalIdentity.identity_group_id.is_(None),
                        CanonicalIdentity.id.is_(None),
                    ),
                    Contact.id,
                ),
                else_=None,
            ).label("identity_contact_id"),
            case(
                (
                    and_(
                        CanonicalIdentity.identity_group_id.is_(None),
                        CanonicalIdentity.id.is_(None),
                    ),
                    Chat.account_id,
                ),
                else_=None,
            ).label("identity_source_account_id"),
            Contact.id.label("contact_id"),
            Contact.platform.label("platform"),
            Contact.platform_user_id.label("contact_platform_user_id"),
            Contact.display_name.label("display_name"),
        )
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == Account.platform,
        )
        .join(peers, peers.c.chat_id == Chat.id)
        .join(single_peer_chats, single_peer_chats.c.chat_id == Chat.id)
        .join(
            Contact,
            and_(
                Contact.account_id == Chat.account_id,
                Contact.platform == Chat.platform,
                Contact.platform_user_id == peers.c.peer_platform_user_id,
            ),
        )
        .outerjoin(
            CanonicalIdentity,
            CanonicalIdentity.id == Contact.canonical_identity_id,
        )
        .cte("forgotten_eligible_pairs")
    )

    ordinary_message = Message.message_type == ORDINARY_MESSAGE_TYPE
    owner_direction = (
        select(owner_account.id)
        .where(
            owner_account.platform == Message.platform,
            owner_account.platform_user_id == Message.sender_id,
        )
        .exists()
    )
    contact_direction = and_(
        Message.platform == eligible_pairs.c.platform,
        Message.sender_id == eligible_pairs.c.contact_platform_user_id,
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
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
            eligible_pairs.c.identity_source_account_id,
            func.min(eligible_pairs.c.contact_id).label("contact_id"),
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
        .where(Message.platform == eligible_pairs.c.platform)
        .group_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
            eligible_pairs.c.identity_source_account_id,
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
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
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
            Message.platform == eligible_pairs.c.platform,
            Message.message_date.is_not(None),
            dated_message,
        )
        .group_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.canonical_identity_id,
            eligible_pairs.c.identity_contact_id,
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
