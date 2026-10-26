from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import Account, Chat, Contact, Message
from app.models import CanonicalIdentity
from app.schemas.analytics import (
    CommunicationTimelineMonth,
    CommunicationTimelineStatistics,
    CommunicationTimelineSummary,
)

from .analytics_constants import ORDINARY_MESSAGE_TYPE


def _utc_month_expression(db: Session, message_date: Any) -> Any:
    if db.get_bind().dialect.name == "postgresql":
        return func.to_char(func.timezone("UTC", message_date), "YYYY-MM")
    return func.strftime("%Y-%m", message_date)


def _utc_date_expression(db: Session, message_date: Any) -> Any:
    if db.get_bind().dialect.name == "postgresql":
        return func.date(func.timezone("UTC", message_date))
    return func.date(message_date)


def _count_when(condition: Any) -> Any:
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


def build_communication_timeline_statistics(
    db: Session,
    *,
    canonical_identity_id: int | None = None,
) -> CommunicationTimelineStatistics:
    identity_group_id = (
        db.scalar(
            select(CanonicalIdentity.identity_group_id).where(
                CanonicalIdentity.id == canonical_identity_id
            )
        )
        if canonical_identity_id is not None
        else None
    )
    if identity_group_id is None:
        identity_ids = select(CanonicalIdentity.id).where(
            CanonicalIdentity.id == canonical_identity_id
        )
    else:
        identity_ids = select(CanonicalIdentity.id).where(
            CanonicalIdentity.identity_group_id == identity_group_id
        )
    contact_pairs = None
    if canonical_identity_id is not None:
        contact_pairs = (
            select(
                Chat.id.label("chat_id"),
                Chat.account_id.label("account_id"),
                Contact.id.label("contact_id"),
                Contact.platform.label("platform"),
            )
            .join(Contact, Contact.account_id == Chat.account_id)
            .join(
                Message,
                and_(
                    Message.chat_id == Chat.id,
                    or_(
                        Message.sender_id == Contact.platform_user_id,
                        and_(
                            Message.sender_id.is_(None),
                            Message.sender_contact_id == Contact.id,
                        ),
                    ),
                ),
            )
            .where(
                Chat.platform == Contact.platform,
                Message.platform == Contact.platform,
                Chat.chat_type == "personal_chat",
                Message.message_type == ORDINARY_MESSAGE_TYPE,
                Contact.canonical_identity_id.in_(identity_ids),
            )
            .distinct()
            .cte("timeline_contact_pairs")
        )
        relevant_chats = (
            select(contact_pairs.c.chat_id)
            .distinct()
            .cte("timeline_relevant_chats")
        )

    scoped_messages_statement = (
        select(
            Message.id.label("message_id"),
            Message.sender_id.label("sender_telegram_id"),
            Message.sender_contact_id.label("sender_contact_id"),
            Message.platform.label("platform"),
            Message.is_outgoing.label("is_outgoing"),
            Message.message_date.label("message_date"),
            Chat.account_id.label("account_id"),
        )
        .join(Chat, Chat.id == Message.chat_id)
        .where(
            Chat.platform == Message.platform,
            Message.message_type == ORDINARY_MESSAGE_TYPE,
        )
    )
    if canonical_identity_id is not None:
        scoped_messages_statement = scoped_messages_statement.join(
            relevant_chats,
            relevant_chats.c.chat_id == Chat.id,
        )
    scoped_messages = scoped_messages_statement.cte("timeline_messages")

    sender_id = scoped_messages.c.sender_telegram_id
    owner_account = aliased(Account)
    owner_direction = (
        select(owner_account.id)
        .where(
            owner_account.platform == scoped_messages.c.platform,
            owner_account.platform_user_id == sender_id,
        )
        .exists()
    )
    if canonical_identity_id is None:
        contact_direction = and_(
            sender_id.is_not(None),
            ~owner_direction,
            scoped_messages.c.is_outgoing.is_(False),
        )
    else:
        contact_ids = select(Contact.id).where(
            Contact.canonical_identity_id.in_(identity_ids)
        )
        contact_platform_ids = select(Contact.platform_user_id).where(
            Contact.platform == scoped_messages.c.platform,
            Contact.canonical_identity_id.in_(identity_ids),
        )
        matching_contact = or_(
            sender_id.in_(contact_platform_ids),
            scoped_messages.c.sender_contact_id.in_(contact_ids),
        )
        consistent_sender = or_(
            sender_id.is_(None),
            sender_id.in_(contact_platform_ids),
        )
        contact_direction = and_(
            matching_contact,
            consistent_sender,
            scoped_messages.c.is_outgoing.is_(False),
        )

    unknown_direction = case(
        (owner_direction, 0),
        (contact_direction, 0),
        else_=1,
    )
    utc_date = _utc_date_expression(db, scoped_messages.c.message_date)
    month_expression = _utc_month_expression(db, scoped_messages.c.message_date)

    summary_statement = select(
        func.count().label("ordinary_message_count"),
        _count_when(scoped_messages.c.message_date.is_not(None)).label(
            "dated_ordinary_message_count"
        ),
        _count_when(scoped_messages.c.message_date.is_(None)).label(
            "undated_ordinary_message_count"
        ),
        _count_when(owner_direction).label("owner_message_count"),
        _count_when(contact_direction).label("contact_message_count"),
        _count_when(unknown_direction == 1).label(
            "unknown_direction_message_count"
        ),
        _count_when(
            and_(scoped_messages.c.message_date.is_(None), owner_direction)
        ).label("undated_owner_message_count"),
        _count_when(
            and_(scoped_messages.c.message_date.is_(None), contact_direction)
        ).label("undated_contact_message_count"),
        _count_when(
            and_(scoped_messages.c.message_date.is_(None), unknown_direction == 1)
        ).label("undated_unknown_direction_message_count"),
    ).select_from(scoped_messages)
    summary_row = db.execute(summary_statement).one()

    month_statement = (
        select(
            month_expression.label("month"),
            func.count().label("ordinary_message_count"),
            _count_when(owner_direction).label("owner_message_count"),
            _count_when(contact_direction).label("contact_message_count"),
            _count_when(unknown_direction == 1).label(
                "unknown_direction_message_count"
            ),
            func.count(func.distinct(utc_date)).label("active_days"),
            func.count(
                func.distinct(case((owner_direction, utc_date), else_=None))
            ).label("owner_active_days"),
            func.count(
                func.distinct(case((contact_direction, utc_date), else_=None))
            ).label("contact_active_days"),
            func.count(
                func.distinct(
                    case((unknown_direction == 1, utc_date), else_=None)
                )
            ).label("unknown_direction_active_days"),
        )
        .select_from(scoped_messages)
        .where(scoped_messages.c.message_date.is_not(None))
        .group_by(month_expression)
        .order_by(month_expression)
    )
    month_rows = list(db.execute(month_statement))

    if canonical_identity_id is None:
        source_accounts = list(
            db.execute(
                select(
                    Account.id,
                    Account.username,
                    Account.name,
                )
                .order_by(Account.id)
            )
        )
        source_contact_ids: list[int] = []
    else:
        source_rows = list(
            db.execute(
                select(
                    contact_pairs.c.account_id,
                    contact_pairs.c.contact_id,
                    Account.username,
                    Account.name,
                )
                .join(
                    Account,
                    Account.id == contact_pairs.c.account_id,
                )
                .distinct()
                .order_by(contact_pairs.c.account_id, contact_pairs.c.contact_id)
            )
        )
        accounts_by_id = {
            row.account_id: row
            for row in source_rows
        }
        source_accounts = [
            (
                account_id,
                accounts_by_id[account_id].username,
                accounts_by_id[account_id].name,
            )
            for account_id in sorted(accounts_by_id)
        ]
        source_contact_ids = sorted({row.contact_id for row in source_rows})

    monthly_counts = {
        row.month: {
            "ordinary_message_count": int(row.ordinary_message_count),
            "owner_message_count": int(row.owner_message_count),
            "contact_message_count": int(row.contact_message_count),
            "unknown_direction_message_count": int(
                row.unknown_direction_message_count
            ),
            "active_days": int(row.active_days),
            "owner_active_days": int(row.owner_active_days),
            "contact_active_days": int(row.contact_active_days),
            "unknown_direction_active_days": int(
                row.unknown_direction_active_days
            ),
        }
        for row in month_rows
    }
    months: list[CommunicationTimelineMonth] = []
    if monthly_counts:
        first_month = date.fromisoformat(f"{min(monthly_counts)}-01")
        last_month = date.fromisoformat(f"{max(monthly_counts)}-01")
        month = first_month
        while month <= last_month:
            month_label = month.strftime("%Y-%m")
            months.append(
                CommunicationTimelineMonth(
                    month=month_label,
                    **monthly_counts.get(
                        month_label,
                        {
                            "ordinary_message_count": 0,
                            "owner_message_count": 0,
                            "contact_message_count": 0,
                            "unknown_direction_message_count": 0,
                            "active_days": 0,
                            "owner_active_days": 0,
                            "contact_active_days": 0,
                            "unknown_direction_active_days": 0,
                        },
                    ),
                )
            )
            month = (month + timedelta(days=32)).replace(day=1)

    account_ids = [row[0] for row in source_accounts]
    return CommunicationTimelineStatistics(
        summary=CommunicationTimelineSummary(
            scope="contact" if canonical_identity_id is not None else "owner",
            canonical_identity_id=canonical_identity_id,
            identity_group_id=identity_group_id,
            source_account_count=len(account_ids),
            source_account_ids=account_ids,
            source_account_labels=[
                f"@{username}" if username else name
                for _, username, name in source_accounts
            ],
            source_contact_ids=source_contact_ids,
            ordinary_message_count=int(summary_row.ordinary_message_count),
            dated_ordinary_message_count=int(
                summary_row.dated_ordinary_message_count
            ),
            undated_ordinary_message_count=int(
                summary_row.undated_ordinary_message_count
            ),
            owner_message_count=int(summary_row.owner_message_count),
            contact_message_count=int(summary_row.contact_message_count),
            unknown_direction_message_count=int(
                summary_row.unknown_direction_message_count
            ),
            undated_owner_message_count=int(
                summary_row.undated_owner_message_count
            ),
            undated_contact_message_count=int(
                summary_row.undated_contact_message_count
            ),
            undated_unknown_direction_message_count=int(
                summary_row.undated_unknown_direction_message_count
            ),
        ),
        months=months,
    )
