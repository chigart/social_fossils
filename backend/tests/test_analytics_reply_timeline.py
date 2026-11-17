from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from analytics_test_helpers import add_account, add_chat, add_message
from app.routers.analytics_overview import get_chat_statistics
from app.routers.analytics_reply_timeline import get_owner_reply_timeline


def _add_message(
    db_session,
    *,
    message_id: int,
    chat_id: int,
    message_date: datetime,
    sender_id: str,
    is_outgoing: bool | None,
    message_type: str = "message",
):
    add_message(
        db_session,
        message_id,
        chat_id,
        message_type,
        sender_id,
        message_date=message_date,
        is_outgoing=is_outgoing,
        telegram_message_id=str(message_id),
    )


def test_owner_reply_timeline_counts_one_first_reply_per_contact_opened_session(
    db_session,
):
    add_account(db_session, 1, "owner")
    add_account(db_session, 2, "second-owner")
    add_account(db_session, 3, "instagram-owner")
    add_account(db_session, 4, "vk-owner")
    add_chat(db_session, 10, 1, "dm", chat_type="personal_chat")
    add_chat(db_session, 20, 1, "group", chat_type="private_group")
    add_chat(db_session, 30, 2, "second-account-dm", chat_type="personal_chat")
    add_chat(db_session, 40, 1, "second-year-dm", chat_type="personal_chat")
    add_chat(db_session, 50, 1, "long-gap-dm", chat_type="personal_chat")
    add_chat(db_session, 60, 1, "contact-response-dm", chat_type="personal_chat")
    add_chat(db_session, 70, 1, "new-session-dm", chat_type="personal_chat")
    add_chat(db_session, 80, 3, "instagram-dm", chat_type="personal_chat")
    add_chat(db_session, 90, 4, "vk-dm", chat_type="personal_chat")

    messages = [
        (1, 10, datetime(2022, 1, 1, tzinfo=timezone.utc), "peer", False),
        (21, 10, datetime(2022, 1, 1, 0, 30, tzinfo=timezone.utc), "peer", False),
        (22, 10, datetime(2022, 1, 1, 1, tzinfo=timezone.utc), "owner", True),
        (23, 10, datetime(2022, 1, 1, 1, 10, tzinfo=timezone.utc), "owner", True),
        (3, 10, datetime(2022, 3, 1, tzinfo=timezone.utc), "peer", False),
        (4, 10, datetime(2022, 3, 1, 3, tzinfo=timezone.utc), "owner", True),
        (5, 20, datetime(2022, 1, 1, tzinfo=timezone.utc), "peer", False),
        (6, 20, datetime(2022, 1, 1, 1, tzinfo=timezone.utc), "owner", True),
        (7, 30, datetime(2022, 10, 1, tzinfo=timezone.utc), "peer", False),
        (8, 30, datetime(2022, 10, 1, 5, tzinfo=timezone.utc), "owner", True),
        (9, 40, datetime(2023, 1, 1, tzinfo=timezone.utc), "peer", False),
        (10, 40, datetime(2023, 1, 1, 0, 30, tzinfo=timezone.utc), "owner", True),
        (11, 50, datetime(2022, 1, 1, tzinfo=timezone.utc), "peer", False),
        (12, 50, datetime(2022, 2, 2, tzinfo=timezone.utc), "owner", True),
        (13, 60, datetime(2022, 1, 1, tzinfo=timezone.utc), "owner", True),
        (14, 60, datetime(2022, 1, 1, 1, tzinfo=timezone.utc), "peer", False),
        (15, 70, datetime(2022, 1, 1, tzinfo=timezone.utc), "peer", False),
        (16, 70, datetime(2022, 1, 1, 13, tzinfo=timezone.utc), "owner", True),
        (17, 80, datetime(2022, 7, 1, tzinfo=timezone.utc), "peer", False),
        (18, 80, datetime(2022, 7, 1, 2, tzinfo=timezone.utc), "owner", True),
        (19, 90, datetime(2022, 8, 1, tzinfo=timezone.utc), "peer", False),
        (20, 90, datetime(2022, 8, 1, 4, tzinfo=timezone.utc), "owner", True),
    ]
    for message_id, chat_id, message_date, sender_id, is_outgoing in messages:
        _add_message(
            db_session,
            message_id=message_id,
            chat_id=chat_id,
            message_date=message_date,
            sender_id=sender_id,
            is_outgoing=is_outgoing,
        )
    for account_id, platform in (
        (2, "facebook"),
        (3, "instagram"),
        (4, "vk"),
    ):
        db_session.execute(
            text("UPDATE account SET platform = :platform WHERE id = :account_id"),
            {"platform": platform, "account_id": account_id},
        )
        db_session.execute(
            text("UPDATE chats SET platform = :platform WHERE account_id = :account_id"),
            {"platform": platform, "account_id": account_id},
        )
        db_session.execute(
            text(
                "UPDATE messages SET platform = :platform "
                "WHERE chat_id IN (SELECT id FROM chats WHERE account_id = :account_id)"
            ),
            {"platform": platform, "account_id": account_id},
        )

    timeline = get_owner_reply_timeline(db_session)

    assert [
        (year.year, year.average_response_seconds)
        for year in timeline.years
    ] == [
        (2022, 10800.0),
        (2023, None),
    ]


def test_owner_reply_timeline_requires_five_samples_per_year(db_session):
    add_account(db_session, 1, "owner")
    add_chat(db_session, 10, 1, "dm", chat_type="personal_chat")
    start = datetime(2022, 1, 1, tzinfo=timezone.utc)
    for index in range(5):
        session_start = start + timedelta(days=index)
        _add_message(
            db_session,
            message_id=index * 2 + 1,
            chat_id=10,
            message_date=session_start,
            sender_id="peer",
            is_outgoing=False,
        )
        _add_message(
            db_session,
            message_id=index * 2 + 2,
            chat_id=10,
            message_date=session_start + timedelta(minutes=10),
            sender_id="owner",
            is_outgoing=True,
        )

    timeline = get_owner_reply_timeline(db_session)

    assert [(year.year, year.average_response_seconds) for year in timeline.years] == [
        (2022, 600.0)
    ]


def test_owner_reply_timeline_includes_unmeasured_history_years_as_na(db_session):
    add_account(db_session, 1, "owner")
    add_chat(db_session, 10, 1, "dm", chat_type="personal_chat")
    for message_id, message_date in (
        (1, datetime(2018, 1, 1, tzinfo=timezone.utc)),
        (2, datetime(2026, 1, 1, tzinfo=timezone.utc)),
    ):
        _add_message(
            db_session,
            message_id=message_id,
            chat_id=10,
            message_date=message_date,
            sender_id="peer",
            is_outgoing=False,
        )

    timeline = get_owner_reply_timeline(db_session)

    assert [
        (year.year, year.average_response_seconds)
        for year in timeline.years
    ] == [
        (year, None) for year in range(2018, 2027)
    ]


def test_owner_reply_timeline_excludes_reply_after_first_12_hours(db_session):
    add_account(db_session, 1, "owner")
    add_chat(db_session, 10, 1, "dm", chat_type="personal_chat")
    start = datetime(2022, 1, 1, tzinfo=timezone.utc)
    messages = [
        (1, start, "peer", False),
        (2, start + timedelta(hours=10), "peer", False),
        (3, start + timedelta(hours=19), "peer", False),
        (4, start + timedelta(hours=19, minutes=48), "owner", True),
    ]
    for message_id, message_date, sender_id, is_outgoing in messages:
        _add_message(
            db_session,
            message_id=message_id,
            chat_id=10,
            message_date=message_date,
            sender_id=sender_id,
            is_outgoing=is_outgoing,
        )

    timeline = get_owner_reply_timeline(db_session)

    assert len(timeline.years) == 1
    assert timeline.years[0].average_response_seconds is None


def test_owner_reply_timeline_includes_other_platforms(db_session):
    add_account(db_session, 1, "owner")
    add_chat(db_session, 10, 1, "dm", chat_type="personal_chat")
    db_session.execute(
        text("UPDATE account SET platform = 'facebook' WHERE id = 1")
    )
    db_session.execute(
        text("UPDATE chats SET platform = 'facebook' WHERE id = 10")
    )
    for message_id, message_date, sender_id, is_outgoing in (
        (1, datetime(2022, 1, 1, tzinfo=timezone.utc), "peer", False),
        (2, datetime(2022, 1, 1, 1, tzinfo=timezone.utc), "owner", True),
    ):
        _add_message(
            db_session,
            message_id=message_id,
            chat_id=10,
            message_date=message_date,
            sender_id=sender_id,
            is_outgoing=is_outgoing,
        )
    db_session.execute(
        text("UPDATE messages SET platform = 'facebook' WHERE chat_id = 10")
    )

    timeline = get_owner_reply_timeline(db_session)

    assert [
        (year.year, year.average_response_seconds)
        for year in timeline.years
    ] == [(2022, None)]
    dm_statistics = get_chat_statistics(db_session, chat_scope="dm")

    assert dm_statistics.items[0].average_response_seconds is None
