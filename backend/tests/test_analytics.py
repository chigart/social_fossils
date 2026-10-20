from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.main import app
from app.routers.analytics import (
    get_chat_statistics,
    get_contact_statistics,
    get_overview,
)
from app.schemas.analytics import (
    ChatStatistics,
    ContactStatistics,
    OverviewStatistics,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE telegram_accounts ("
            "id INTEGER PRIMARY KEY, telegram_user_id VARCHAR(100))"
        ))
        connection.execute(text(
            "CREATE TABLE contacts ("
            "id INTEGER PRIMARY KEY, account_id INTEGER, "
            "telegram_user_id VARCHAR(100), display_name VARCHAR(300))"
        ))
        connection.execute(text(
            "CREATE TABLE chats ("
            "id INTEGER PRIMARY KEY, account_id INTEGER, "
            "telegram_chat_id VARCHAR(100), title VARCHAR(300), "
            "chat_type VARCHAR(50))"
        ))
        connection.execute(text(
            "CREATE TABLE messages ("
            "id INTEGER PRIMARY KEY, chat_id INTEGER, "
            "sender_telegram_id VARCHAR(100), sender_contact_id INTEGER, "
            "sender_name VARCHAR(300), is_outgoing BOOLEAN, "
            "message_date DATETIME, message_type VARCHAR(50))"
        ))

    with Session(engine) as session:
        yield session
    engine.dispose()


def add_account(db_session, account_id: int, telegram_user_id: str | None):
    db_session.execute(
        text("INSERT INTO telegram_accounts (id, telegram_user_id) VALUES (:id, :user_id)"),
        {"id": account_id, "user_id": telegram_user_id},
    )


def add_chat(
    db_session,
    chat_id: int,
    account_id: int,
    telegram_chat_id: str,
    title: str | None = None,
):
    db_session.execute(
        text(
            "INSERT INTO chats (id, account_id, telegram_chat_id, title, chat_type) "
            "VALUES (:id, :account_id, :telegram_id, :title, 'private')"
        ),
        {
            "id": chat_id,
            "account_id": account_id,
            "telegram_id": telegram_chat_id,
            "title": title,
        },
    )


def add_message(
    db_session,
    message_id: int,
    chat_id: int,
    message_type: str,
    sender_id: str | None,
    message_date: datetime | None = None,
    is_outgoing: bool | None = None,
    sender_contact_id: int | None = None,
):
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, message_type, sender_telegram_id, message_date, "
            "is_outgoing, sender_contact_id) "
            "VALUES (:id, :chat_id, :message_type, :sender_id, :message_date, "
            ":is_outgoing, :contact_id)"
        ),
        {
            "id": message_id,
            "chat_id": chat_id,
            "message_type": message_type,
            "sender_id": sender_id,
            "message_date": message_date,
            "is_outgoing": is_outgoing,
            "contact_id": sender_contact_id,
        },
    )
    db_session.flush()


def test_empty_database_returns_zeroes_and_empty_lists(db_session):
    overview = get_overview(db_session)

    assert OverviewStatistics.model_validate(overview).model_dump() == {
        "total_imported_accounts": 0,
        "total_chats": 0,
        "total_messages": 0,
        "total_ordinary_messages": 0,
        "total_service_messages": 0,
        "earliest_message_timestamp": None,
        "latest_message_timestamp": None,
    }
    assert get_chat_statistics(db_session) == []
    assert get_contact_statistics(db_session) == []
    assert set(app.openapi()["paths"]) >= {
        "/api/analytics/overview",
        "/api/analytics/chats",
        "/api/analytics/contacts",
    }


def test_account_without_messages_and_empty_chat_are_included(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "telegram-chat-10", "No messages")

    overview = get_overview(db_session)
    chats = get_chat_statistics(db_session)

    assert overview.total_imported_accounts == 1
    assert overview.total_chats == 1
    assert overview.total_messages == 0
    assert overview.earliest_message_timestamp is None
    assert len(chats) == 1
    assert ChatStatistics.model_validate(chats[0]).model_dump() == {
        "chat_id": 10,
        "telegram_chat_id": "telegram-chat-10",
        "title": "No messages",
        "chat_type": "private",
        "total_messages": 0,
        "ordinary_messages": 0,
        "service_messages": 0,
        "earliest_message_timestamp": None,
        "latest_message_timestamp": None,
        "distinct_identified_senders": 0,
    }


def test_aggregates_types_dates_senders_contacts_and_owner(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "telegram-chat-10", "Active")
    add_chat(db_session, 11, 1, "telegram-chat-11", "Second")
    add_chat(db_session, 12, 1, "telegram-chat-12", "Empty")
    db_session.execute(
        text(
            "INSERT INTO contacts (id, account_id, telegram_user_id, display_name) "
            "VALUES (20, 1, 'user-alex', 'Alex'), (21, 1, 'user-sam', 'Sam')"
        )
    )

    first_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    second_date = datetime(2025, 1, 2, tzinfo=timezone.utc)
    latest_date = datetime(2025, 1, 5, tzinfo=timezone.utc)
    add_message(db_session, 1, 10, "message", "user-alex", first_date, sender_contact_id=20)
    add_message(db_session, 2, 10, "service", "user-sam", sender_contact_id=21)
    add_message(db_session, 3, 10, "message", None, second_date)
    add_message(db_session, 4, 10, "message", "user-owner", is_outgoing=True)
    add_message(db_session, 5, 10, "service", "user-unlinked", latest_date)
    add_message(db_session, 6, 11, "message", "user-alex", second_date)

    overview = OverviewStatistics.model_validate(get_overview(db_session))
    chats = [ChatStatistics.model_validate(chat) for chat in get_chat_statistics(db_session)]
    contacts = [
        ContactStatistics.model_validate(contact)
        for contact in get_contact_statistics(db_session)
    ]

    assert overview.total_imported_accounts == 1
    assert overview.total_chats == 3
    assert overview.total_messages == 6
    assert overview.total_ordinary_messages == 4
    assert overview.total_service_messages == 2
    assert overview.earliest_message_timestamp == first_date
    assert overview.latest_message_timestamp == latest_date

    by_chat_id = {chat.chat_id: chat for chat in chats}
    assert by_chat_id[10].telegram_chat_id == "telegram-chat-10"
    assert by_chat_id[10].total_messages == 5
    assert by_chat_id[10].ordinary_messages == 3
    assert by_chat_id[10].service_messages == 2
    assert by_chat_id[10].distinct_identified_senders == 4
    assert by_chat_id[11].total_messages == 1
    assert by_chat_id[11].distinct_identified_senders == 1
    assert by_chat_id[12].total_messages == 0

    by_sender = {contact.telegram_user_id: contact for contact in contacts}
    assert set(by_sender) == {"user-alex", "user-sam", "user-unlinked", None}
    assert by_sender["user-alex"].contact_id == 20
    assert by_sender["user-alex"].total_messages_sent == 2
    assert by_sender["user-alex"].ordinary_messages_sent == 2
    assert by_sender["user-sam"].service_events_attributed == 1
    assert by_sender["user-unlinked"].contact_id is None
    assert by_sender["user-unlinked"].service_events_attributed == 1
    assert by_sender[None].total_messages_sent == 1


def test_nonstandard_message_type_only_contributes_to_total(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "telegram-chat-10")
    add_message(db_session, 1, 10, "unknown_event", "user-other")

    overview = get_overview(db_session)
    contact = get_contact_statistics(db_session)[0]

    assert overview.total_messages == 1
    assert overview.total_ordinary_messages == 0
    assert overview.total_service_messages == 0
    assert contact.total_messages_sent == 1
    assert contact.ordinary_messages_sent == 0
    assert contact.service_events_attributed == 0