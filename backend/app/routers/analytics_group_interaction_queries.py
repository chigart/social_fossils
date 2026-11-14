from datetime import datetime

from sqlalchemy import String, and_, case, cast, func, or_, select, union_all
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.selectable import CTE, Select

from app.constants import ORDINARY_MESSAGE_TYPE
from app.models import Account, CanonicalIdentity, Chat, Contact, Message


def build_group_message_days(
    db: Session,
    recent_start: datetime,
    current_time: datetime,
    target_contact_id: int | None = None,
) -> CTE:
    # Split days at the exact cutoff while reducing repeated messages per sender.
    day = (
        func.date(func.timezone("UTC", Message.message_date))
        if db.get_bind().dialect.name == "postgresql"
        else func.date(Message.message_date)
    )
    period = case(
        (Message.message_date < recent_start, "historical"),
        (Message.message_date <= current_time, "recent"),
        else_="other",
    )
    statement = (
        select(
            Message.chat_id,
            Message.platform,
            Message.sender_id,
            Message.is_outgoing,
            day.label("day"),
            period.label("period"),
            func.count().label("message_count"),
            func.sum(func.length(func.coalesce(Message.text_content, ""))).label(
                "text_length"
            ),
            func.min(Message.message_date).label("first_message_at"),
            func.max(Message.message_date).label("last_message_at"),
        )
        .join(Chat, Chat.id == Message.chat_id)
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.chat_type != "personal_chat",
            Chat.platform == Account.platform,
            Account.platform_user_id.is_not(None),
            Message.platform == Chat.platform,
            Message.message_type == ORDINARY_MESSAGE_TYPE,
        )
    )
    if target_contact_id is not None:
        target = db.execute(
            select(
                Contact.id,
                Contact.canonical_identity_id,
                CanonicalIdentity.identity_group_id,
            )
            .outerjoin(
                CanonicalIdentity, CanonicalIdentity.id == Contact.canonical_identity_id
            )
            .where(Contact.id == target_contact_id)
        ).one_or_none()
        if target is None:
            target_filter = Contact.id == target_contact_id
        elif target.identity_group_id is not None:
            target_filter = (
                CanonicalIdentity.identity_group_id == target.identity_group_id
            )
        elif target.canonical_identity_id is not None:
            target_filter = (
                Contact.canonical_identity_id == target.canonical_identity_id
            )
        else:
            target_filter = Contact.id == target.id

        peer_message = aliased(Message)
        peer_chat = aliased(Chat)
        target_peers = (
            select(
                peer_message.chat_id.label("chat_id"),
                peer_message.sender_id.label("sender_id"),
            )
            .join(peer_chat, peer_chat.id == peer_message.chat_id)
            .join(
                Contact,
                and_(
                    Contact.account_id == peer_chat.account_id,
                    Contact.platform == peer_chat.platform,
                    Contact.platform_user_id == peer_message.sender_id,
                ),
            )
            .outerjoin(
                CanonicalIdentity, CanonicalIdentity.id == Contact.canonical_identity_id
            )
            .where(
                target_filter,
                peer_chat.chat_type != "personal_chat",
                peer_message.platform == peer_chat.platform,
                peer_message.message_type == ORDINARY_MESSAGE_TYPE,
            )
            .distinct()
            .cte("target_group_peers")
        )
        target_chats = (
            select(target_peers.c.chat_id).distinct().cte("target_group_chats")
        )
        selected_message = aliased(Message)
        owner = aliased(Account)
        target_message_ids = union_all(
            select(selected_message.id).join(
                target_peers,
                and_(
                    target_peers.c.chat_id == selected_message.chat_id,
                    target_peers.c.sender_id == selected_message.sender_id,
                ),
            ),
            select(selected_message.id)
            .join(target_chats, target_chats.c.chat_id == selected_message.chat_id)
            .join(
                owner,
                and_(
                    owner.platform == selected_message.platform,
                    owner.platform_user_id == selected_message.sender_id,
                ),
            )
            .distinct(),
        )
        statement = statement.where(Message.id.in_(target_message_ids))
    return (
        statement.group_by(
            Message.chat_id,
            Message.platform,
            Message.sender_id,
            Message.is_outgoing,
            day,
            period,
        )
        .cte("group_message_days")
    )


def build_group_interaction_statements(
    eligible_pairs: CTE, days: CTE
) -> tuple[Select, Select]:
    owner = aliased(Account)
    owner_direction = (
        select(owner.id)
        .where(
            owner.platform == days.c.platform,
            owner.platform_user_id == days.c.sender_id,
        )
        .exists()
    )
    contact_sender = days.c.sender_id == eligible_pairs.c.contact_platform_user_id
    contact_direction = and_(contact_sender, days.c.is_outgoing.is_(False))
    known_direction = or_(owner_direction, contact_direction)
    historical = days.c.period == "historical"
    recent = days.c.period == "recent"
    dated = or_(historical, recent)

    def sum_when(condition, value):
        return func.coalesce(func.sum(case((condition, value), else_=0)), 0)

    identity_columns = (
        eligible_pairs.c.identity_group_id,
        eligible_pairs.c.canonical_identity_id,
        eligible_pairs.c.identity_contact_id,
        eligible_pairs.c.identity_source_account_id,
    )
    join_condition = and_(
        days.c.chat_id == eligible_pairs.c.chat_id,
        days.c.platform == eligible_pairs.c.platform,
        or_(owner_direction, contact_sender),
    )
    aggregate = (
        select(
            *identity_columns,
            func.min(eligible_pairs.c.contact_id).label("contact_id"),
            func.min(eligible_pairs.c.display_name).label("display_name"),
            func.count(func.distinct(eligible_pairs.c.chat_id)).label(
                "interaction_chat_count"
            ),
            sum_when(owner_direction, days.c.message_count).label("owner_message_count"),
            sum_when(contact_direction, days.c.message_count).label("contact_message_count"),
            sum_when(owner_direction, days.c.text_length).label("owner_text_length"),
            sum_when(contact_direction, days.c.text_length).label("contact_text_length"),
            sum_when(known_direction, days.c.message_count).label("known_message_count"),
            func.sum(days.c.message_count).label("ordinary_message_count"),
            func.min(case((and_(known_direction, dated), days.c.first_message_at))).label(
                "first_message_at"
            ),
            func.max(case((and_(known_direction, dated), days.c.last_message_at))).label(
                "last_message_at"
            ),
            func.count(func.distinct(case((and_(known_direction, dated), days.c.day)))).label(
                "distinct_active_days"
            ),
            sum_when(and_(known_direction, historical), days.c.message_count).label(
                "historical_message_count"
            ),
            func.min(
                case((and_(known_direction, historical), days.c.first_message_at))
            ).label("historical_first_message_at"),
            func.max(
                case((and_(known_direction, historical), days.c.last_message_at))
            ).label("historical_last_message_at"),
            func.count(
                func.distinct(case((and_(known_direction, historical), days.c.day)))
            ).label("historical_active_days"),
            sum_when(and_(owner_direction, recent), days.c.message_count).label(
                "recent_owner_message_count"
            ),
            sum_when(and_(contact_direction, recent), days.c.message_count).label(
                "recent_contact_message_count"
            ),
        )
        .select_from(eligible_pairs)
        .join(days, join_condition)
        .group_by(*identity_columns)
    )
    month = func.substr(cast(days.c.day, String), 1, 7)
    monthly = (
        select(
            *identity_columns,
            month.label("month"),
            sum_when(and_(historical, owner_direction), days.c.message_count).label(
                "historical_owner_message_count"
            ),
            sum_when(and_(historical, contact_direction), days.c.message_count).label(
                "historical_contact_message_count"
            ),
            sum_when(and_(recent, owner_direction), days.c.message_count).label(
                "recent_owner_message_count"
            ),
            sum_when(and_(recent, contact_direction), days.c.message_count).label(
                "recent_contact_message_count"
            ),
        )
        .select_from(eligible_pairs)
        .join(days, join_condition)
        .where(known_direction, dated)
        .group_by(*identity_columns, month)
        .order_by(
            eligible_pairs.c.identity_group_id,
            eligible_pairs.c.identity_source_account_id,
            month,
        )
    )
    return aggregate, monthly
