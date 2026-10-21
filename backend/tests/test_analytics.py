from datetime import datetime, timezone
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.main import app
from app.routers.analytics import (
    build_forgotten_contacts_statistics,
    get_chat_statistics,
    get_communication_balance,
    get_contact_statistics,
    get_overview,
)
from app.schemas.analytics import (
    ChatStatistics,
    CommunicationBalanceStatistics,
    ContactStatistics,
    OverviewStatistics,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE telegram_accounts ("
            "id INTEGER PRIMARY KEY, name VARCHAR(200), "
            "username VARCHAR(100), telegram_user_id VARCHAR(100))"
        ))
        connection.execute(text(
            "CREATE TABLE canonical_identities ("
            "id INTEGER PRIMARY KEY, platform VARCHAR(50), "
            "platform_user_id VARCHAR(100))"
        ))
        connection.execute(text(
            "CREATE TABLE contacts ("
            "id INTEGER PRIMARY KEY, account_id INTEGER, "
            "telegram_user_id VARCHAR(100), canonical_identity_id INTEGER, "
            "display_name VARCHAR(300))"
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
            "message_date DATETIME, message_type VARCHAR(50), "
            "text_content TEXT)"
        ))

    with Session(engine) as session:
        yield session
    engine.dispose()


def add_account(
    db_session,
    account_id: int,
    telegram_user_id: str | None,
    *,
    name: str | None = None,
    username: str | None = None,
):
    db_session.execute(
        text(
            "INSERT INTO telegram_accounts "
            "(id, name, username, telegram_user_id) "
            "VALUES (:id, :name, :username, :user_id)"
        ),
        {
            "id": account_id,
            "name": name or f"Account {account_id}",
            "username": username,
            "user_id": telegram_user_id,
        },
    )


def add_chat(
    db_session,
    chat_id: int,
    account_id: int,
    telegram_chat_id: str,
    title: str | None = None,
    chat_type: str = "private",
):
    db_session.execute(
        text(
            "INSERT INTO chats (id, account_id, telegram_chat_id, title, chat_type) "
            "VALUES (:id, :account_id, :telegram_id, :title, :chat_type)"
        ),
        {
            "id": chat_id,
            "account_id": account_id,
            "telegram_id": telegram_chat_id,
            "title": title,
            "chat_type": chat_type,
        },
    )


def add_contact(
    db_session,
    contact_id: int,
    account_id: int,
    telegram_user_id: str,
    display_name: str,
):
    identity_id = db_session.scalar(
        text(
            "SELECT id FROM canonical_identities "
            "WHERE platform = 'telegram' AND platform_user_id = :telegram_user_id"
        ),
        {"telegram_user_id": telegram_user_id},
    )
    if identity_id is None:
        db_session.execute(
            text(
                "INSERT INTO canonical_identities (platform, platform_user_id) "
                "VALUES ('telegram', :telegram_user_id)"
            ),
            {"telegram_user_id": telegram_user_id},
        )
        identity_id = db_session.scalar(
            text(
                "SELECT id FROM canonical_identities "
                "WHERE platform = 'telegram' AND platform_user_id = :telegram_user_id"
            ),
            {"telegram_user_id": telegram_user_id},
        )
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(id, account_id, telegram_user_id, canonical_identity_id, display_name) "
            "VALUES (:id, :account_id, :telegram_user_id, :identity_id, :display_name)"
        ),
        {
            "id": contact_id,
            "account_id": account_id,
            "telegram_user_id": telegram_user_id,
            "identity_id": identity_id,
            "display_name": display_name,
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
    text_content: str | None = None,
):
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, message_type, sender_telegram_id, message_date, "
            "is_outgoing, sender_contact_id, text_content) "
            "VALUES (:id, :chat_id, :message_type, :sender_id, :message_date, "
            ":is_outgoing, :contact_id, :text_content)"
        ),
        {
            "id": message_id,
            "chat_id": chat_id,
            "message_type": message_type,
            "sender_id": sender_id,
            "message_date": message_date,
            "is_outgoing": is_outgoing,
            "contact_id": sender_contact_id,
            "text_content": text_content,
        },
    )
    db_session.flush()


FORGOTTEN_AS_OF = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
HISTORICAL_ACTIVITY_DATES = [
    datetime(2026, 1, 10, tzinfo=timezone.utc),
    datetime(2026, 2, 10, tzinfo=timezone.utc),
    datetime(2026, 3, 10, tzinfo=timezone.utc),
    datetime(2026, 4, 10, tzinfo=timezone.utc),
    datetime(2026, 6, 10, tzinfo=timezone.utc),
]


def add_forgotten_candidate(
    db_session,
    contact_id: int,
    *,
    account_id: int = 1,
    peer_id: str | None = None,
    name: str | None = None,
    chat_type: str = "personal_chat",
) -> tuple[int, str]:
    peer_id = peer_id or f"user-contact-{contact_id}"
    chat_id = account_id * 10_000 + contact_id
    add_contact(
        db_session,
        contact_id,
        account_id,
        peer_id,
        name or f"Contact {contact_id}",
    )
    add_chat(
        db_session,
        chat_id,
        account_id,
        f"telegram-chat-{chat_id}",
        chat_type=chat_type,
    )
    return chat_id, peer_id


def add_exchanges(
    db_session,
    contact_id: int,
    chat_id: int,
    peer_id: str,
    dates: list[datetime | None],
    *,
    exchanges_per_day: int = 5,
    message_id_start: int = 1,
    owner_id: str = "user-owner",
    owner_text: str | None = "owner",
    contact_text: str | None = "contact",
) -> int:
    message_id = contact_id * 10_000 + message_id_start
    for message_date in dates:
        for _ in range(exchanges_per_day):
            add_message(
                db_session,
                message_id,
                chat_id,
                "message",
                owner_id,
                message_date=message_date,
                is_outgoing=True,
                text_content=owner_text,
            )
            message_id += 1
            add_message(
                db_session,
                message_id,
                chat_id,
                "message",
                peer_id,
                message_date=message_date,
                is_outgoing=False,
                sender_contact_id=contact_id,
                text_content=contact_text,
            )
            message_id += 1
    return message_id - contact_id * 10_000


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
    balance = CommunicationBalanceStatistics.model_validate(
        get_communication_balance(db_session)
    )
    assert balance.summary.eligible_contacts == 0
    assert balance.contacts == []
    assert set(app.openapi()["paths"]) >= {
        "/api/analytics/overview",
        "/api/analytics/chats",
        "/api/analytics/contacts",
        "/api/analytics/communication-balance",
        "/api/analytics/forgotten-contacts",
    }
    forgotten_parameters = app.openapi()["paths"][
        "/api/analytics/forgotten-contacts"
    ]["get"]["parameters"]
    assert all(parameter["name"] != "account_id" for parameter in forgotten_parameters)


def test_account_without_messages_and_empty_chat_are_included(db_session):
    add_account(
        db_session,
        1,
        "user-owner",
        name="Ant Malkov",
        username="anton",
    )
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
        "account_id": 1,
        "source_account_label": "@anton",
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


def test_contacts_merge_canonical_peers_but_keep_unlinked_senders_local(db_session):
    add_account(
        db_session,
        1,
        "user-owner-one",
        name="Anton Malkov",
        username="anton",
    )
    add_account(db_session, 2, "user-owner-two", name="Anton Malkov")
    add_chat(db_session, 10, 1, "chat-one")
    add_chat(db_session, 20, 2, "chat-two")
    add_contact(db_session, 20, 1, "user-shared-peer", "Shared peer")
    add_contact(db_session, 30, 2, "user-shared-peer", "Peer name from export two")
    add_contact(db_session, 21, 1, "user-twin-one", "Twin")
    add_contact(db_session, 31, 2, "user-twin-two", "Twin")

    add_message(db_session, 1, 10, "message", "user-shared-peer")
    add_message(db_session, 2, 20, "message", "user-shared-peer")
    add_message(db_session, 3, 10, "message", "user-twin-one")
    add_message(db_session, 4, 20, "message", "user-twin-two")
    add_message(db_session, 5, 10, "message", "user-unlinked")
    add_message(db_session, 6, 20, "message", "user-unlinked")
    add_message(
        db_session,
        7,
        10,
        "message",
        "user-owner-two",
        is_outgoing=False,
    )

    contacts = get_contact_statistics(db_session)
    shared = next(contact for contact in contacts if contact.telegram_user_id == "user-shared-peer")
    twins = [contact for contact in contacts if contact.display_name == "Twin"]
    unlinked = [contact for contact in contacts if contact.telegram_user_id == "user-unlinked"]

    assert shared.total_messages_sent == 2
    assert shared.source_account_ids == [1, 2]
    assert shared.source_account_labels == ["@anton", "Anton Malkov"]
    assert shared.source_contact_ids == [20, 30]
    assert shared.account_id is None
    assert len(twins) == 2
    assert {contact.telegram_user_id for contact in twins} == {
        "user-twin-one",
        "user-twin-two",
    }
    assert len(unlinked) == 2
    assert {contact.account_id for contact in unlinked} == {1, 2}
    assert all(contact.telegram_user_id != "user-owner-two" for contact in contacts)


def test_communication_balance_uses_text_volume_and_excludes_ineligible_data(
    db_session,
):
    add_account(db_session, 1, "user-owner")
    contacts = [
        ("user-long", "Long response"),
        ("user-counts", "Message counts"),
        ("user-owner-heavy", "Owner heavy"),
        ("user-unicode", "Unicode"),
        ("user-empty", "Empty"),
        ("user-unknown", "Unknown direction"),
        ("user-service", "Service"),
        ("user-media", "Media"),
        ("user-group", "Group participant"),
        ("user-second", "Second private sender"),
        ("user-second-peer", "Other peer"),
    ]
    for index, (telegram_user_id, name) in enumerate(contacts, start=20):
        add_contact(db_session, index, 1, telegram_user_id, name)

    for chat_id in range(10, 18):
        add_chat(
            db_session,
            chat_id,
            1,
            f"telegram-chat-{chat_id}",
            chat_type="personal_chat",
        )

    message_id = 1

    def insert(
        chat_id,
        sender_id,
        text_content,
        *,
        outgoing,
        message_type="message",
        message_date=None,
    ):
        nonlocal message_id
        contact_id = next(
            (
                index
                for index, contact in enumerate(contacts, start=20)
                if contact[0] == sender_id
            ),
            None,
        )
        add_message(
            db_session,
            message_id,
            chat_id,
            message_type,
            sender_id,
            message_date=message_date,
            is_outgoing=outgoing,
            sender_contact_id=contact_id,
            text_content=text_content,
        )
        message_id += 1

    first_message_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    last_message_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    for _ in range(3):
        insert(
            10,
            "user-owner",
            "Hi",
            outgoing=True,
            message_date=first_message_at,
        )
    insert(
        10,
        "user-long",
        "R" * 600,
        outgoing=False,
        message_date=last_message_at,
    )

    insert(11, "user-owner", "O" * 250, outgoing=True)
    for _ in range(5):
        insert(11, "user-counts", "C" * 50, outgoing=False)

    insert(12, "user-owner", "O" * 700, outgoing=True)
    insert(12, "user-owner-heavy", "C" * 100, outgoing=False)

    insert(13, "user-owner", "😀" * 250, outgoing=True)
    insert(13, "user-unicode", "é" * 250, outgoing=False)

    insert(14, "user-owner", "", outgoing=True)
    insert(14, "user-empty", "", outgoing=False)

    insert(15, "user-owner", "x" * 499, outgoing=True)
    insert(15, "user-unknown", "not attributed", outgoing=None)
    insert(15, "user-unknown", "inconsistent flag", outgoing=True)

    insert(16, "user-owner", "a" * 300, outgoing=True)
    insert(16, "user-service", "b" * 300, outgoing=False)
    insert(16, "user-service", "service text must not count", outgoing=False, message_type="service")

    insert(17, "user-owner", "mixed text and attachment", outgoing=True)
    insert(17, "user-media", None, outgoing=False)

    add_chat(
        db_session,
        18,
        1,
        "telegram-group",
        chat_type="supergroup",
    )
    insert(18, "user-owner", "group owner text", outgoing=True)
    insert(18, "user-group", "group participant text", outgoing=False)

    add_chat(
        db_session,
        19,
        1,
        "telegram-ambiguous-private",
        chat_type="personal_chat",
    )
    insert(19, "user-owner", "owner text", outgoing=True)
    insert(19, "user-second", "first peer", outgoing=False)
    insert(19, "user-second-peer", "second peer", outgoing=False)

    result = CommunicationBalanceStatistics.model_validate(
        get_communication_balance(db_session)
    )
    by_name = {contact.display_name: contact for contact in result.contacts}

    assert set(by_name) == {
        "Long response",
        "Message counts",
        "Owner heavy",
        "Unicode",
        "Empty",
        "Unknown direction",
        "Service",
        "Media",
    }
    assert by_name["Long response"].classification == "strongly_contact"
    assert by_name["Long response"].owner_text_length == 6
    assert by_name["Long response"].contact_text_length == 600
    assert by_name["Long response"].owner_message_count == 3
    assert by_name["Long response"].contact_message_count == 1
    assert by_name["Long response"].first_message_at == first_message_at
    assert by_name["Long response"].last_message_at == last_message_at
    assert by_name["Long response"].distinct_active_days == 2

    assert by_name["Message counts"].classification == "balanced"
    assert by_name["Message counts"].owner_text_share == 0.5
    assert by_name["Message counts"].owner_share_percentage == 50
    assert by_name["Message counts"].contact_share_percentage == 50
    assert by_name["Message counts"].owner_message_count == 1
    assert by_name["Message counts"].contact_message_count == 5

    assert by_name["Owner heavy"].classification == "strongly_owner"
    assert by_name["Owner heavy"].owner_message_count == 1
    assert by_name["Owner heavy"].contact_message_count == 1
    assert by_name["Unicode"].total_text_length == 500
    assert by_name["Unicode"].classification == "balanced"

    assert by_name["Empty"].total_message_count == 2
    assert by_name["Empty"].total_text_length == 0
    assert by_name["Empty"].owner_text_share is None
    assert by_name["Empty"].contact_text_share is None
    assert by_name["Empty"].classification == "insufficient_data"

    assert by_name["Unknown direction"].owner_text_length == 499
    assert by_name["Unknown direction"].contact_text_length == 0
    assert by_name["Unknown direction"].excluded_unknown_direction_message_count == 2
    assert by_name["Unknown direction"].classification == "insufficient_data"

    assert by_name["Service"].total_text_length == 600
    assert by_name["Service"].total_message_count == 2
    assert by_name["Media"].owner_text_length == len("mixed text and attachment")
    assert by_name["Media"].contact_text_length == 0
    assert by_name["Media"].total_message_count == 2

    assert result.summary.eligible_contacts == 8
    assert result.summary.balanced_contacts == 3
    assert result.summary.mostly_owner_contacts == 0
    assert result.summary.mostly_contact_contacts == 0
    assert result.summary.strongly_owner_contacts == 1
    assert result.summary.strongly_contact_contacts == 1
    assert result.summary.insufficient_data_contacts == 3
    assert result.summary.owner_text_length == (
        6 + 250 + 700 + 250 + 499 + 300 + len("mixed text and attachment")
    )
    assert result.summary.contact_text_length == 600 + 250 + 100 + 250 + 300
    assert result.summary.total_text_length == (
        result.summary.owner_text_length + result.summary.contact_text_length
    )
    assert result.summary.owner_message_count == 10
    assert result.summary.contact_message_count == 11
    assert result.summary.total_message_count == 21
    assert result.summary.excluded_unknown_direction_message_count == 2


def test_communication_balance_combines_owner_aliases_and_canonical_contacts(
    db_session,
):
    add_account(db_session, 1, "user-owner-one", username="anton")
    add_account(db_session, 2, "user-owner-two", username="anton_old")
    for account_id, chat_id, contact_id in ((1, 10, 20), (2, 20, 30)):
        add_chat(
            db_session,
            chat_id,
            account_id,
            f"personal-chat-{chat_id}",
            chat_type="personal_chat",
        )
        add_contact(
            db_session,
            contact_id,
            account_id,
            "user-shared-peer",
            "Shared peer",
        )

    add_message(db_session, 1, 10, "message", "user-owner-one", is_outgoing=True, text_content="owner")
    add_message(db_session, 2, 10, "message", "user-shared-peer", is_outgoing=False, text_content="peer")
    add_message(db_session, 3, 20, "message", "user-owner-two", is_outgoing=True, text_content="owner")
    add_message(db_session, 4, 20, "message", "user-owner-one", is_outgoing=False, text_content="owner")
    add_message(db_session, 5, 20, "message", "user-shared-peer", is_outgoing=False, text_content="peer")

    result = get_communication_balance(db_session)

    assert len(result.contacts) == 1
    contact = result.contacts[0]
    assert contact.canonical_identity_id is not None
    assert contact.source_account_ids == [1, 2]
    assert contact.source_account_labels == ["@anton", "@anton_old"]
    assert contact.source_contact_ids == [20, 30]
    assert contact.owner_message_count == 3
    assert contact.contact_message_count == 2
    assert contact.total_message_count == 5
    assert contact.owner_text_length == len("ownerownerowner")
    assert contact.contact_text_length == len("peerpeer")
    assert result.summary.total_message_count == 5


def test_communication_balance_applies_exact_share_boundaries(db_session):
    add_account(db_session, 1, "user-owner")
    for contact_id, telegram_user_id, name, owner_chars, contact_chars in (
        (20, "user-twenty", "Twenty", 200, 800),
        (21, "user-twenty-one", "Twenty One", 210, 790),
        (22, "user-forty", "Forty", 400, 600),
        (23, "user-sixty", "Sixty", 600, 400),
        (24, "user-seventy-nine", "Seventy Nine", 790, 210),
        (25, "user-eighty", "Eighty", 800, 200),
    ):
        add_contact(db_session, contact_id, 1, telegram_user_id, name)
        add_chat(
            db_session,
            contact_id,
            1,
            f"chat-{contact_id}",
            chat_type="personal_chat",
        )
        add_message(
            db_session,
            contact_id * 10,
            contact_id,
            "message",
            "user-owner",
            is_outgoing=True,
            text_content="o" * owner_chars,
        )
        add_message(
            db_session,
            contact_id * 10 + 1,
            contact_id,
            "message",
            telegram_user_id,
            is_outgoing=False,
            sender_contact_id=contact_id,
            text_content="c" * contact_chars,
        )

    result = get_communication_balance(db_session)
    by_name = {contact.display_name: contact for contact in result.contacts}

    assert by_name["Twenty"].owner_share_percentage == 20
    assert by_name["Twenty"].classification == "strongly_contact"
    assert by_name["Twenty One"].owner_share_percentage == 21
    assert by_name["Twenty One"].classification == "mostly_contact"
    assert by_name["Forty"].owner_text_share == 0.4
    assert by_name["Forty"].owner_share_percentage == 40
    assert by_name["Forty"].classification == "balanced"
    assert by_name["Sixty"].owner_text_share == 0.6
    assert by_name["Sixty"].owner_share_percentage == 60
    assert by_name["Sixty"].classification == "balanced"
    assert by_name["Seventy Nine"].owner_share_percentage == 79
    assert by_name["Seventy Nine"].classification == "mostly_owner"
    assert by_name["Eighty"].owner_share_percentage == 80
    assert by_name["Eighty"].classification == "strongly_owner"


def test_communication_balance_sorts_by_requested_metric(db_session):
    add_account(db_session, 1, "user-owner")
    for contact_id, telegram_user_id, name, owner_text, contact_texts in (
        (20, "user-alex", "Alex", "o" * 800, ["c" * 67, "c" * 67, "c" * 66]),
        (21, "user-zed", "Zed", "o" * 200, ["c" * 800]),
    ):
        add_contact(db_session, contact_id, 1, telegram_user_id, name)
        add_chat(
            db_session,
            contact_id,
            1,
            f"chat-{contact_id}",
            chat_type="personal_chat",
        )
        add_message(
            db_session,
            contact_id * 2,
            contact_id,
            "message",
            "user-owner",
            is_outgoing=True,
            text_content=owner_text,
        )
        for offset, contact_text in enumerate(contact_texts, start=1):
            add_message(
                db_session,
                contact_id * 10 + offset,
                contact_id,
                "message",
                telegram_user_id,
                is_outgoing=False,
                sender_contact_id=contact_id,
                text_content=contact_text,
            )

    by_owner_share = get_communication_balance(db_session, sort_by="owner_share")
    by_message_count = get_communication_balance(db_session, sort_by="message_count")
    by_name = get_communication_balance(db_session, sort_by="display_name")

    assert [contact.display_name for contact in by_owner_share.contacts] == [
        "Zed",
        "Alex",
    ]
    assert [contact.display_name for contact in by_message_count.contacts] == [
        "Alex",
        "Zed",
    ]
    assert [contact.display_name for contact in by_name.contacts] == ["Alex", "Zed"]


def test_forgotten_contacts_classifies_and_ranks_by_history_and_decline(db_session):
    add_account(db_session, 1, "user-owner")
    forgotten_chat, forgotten_peer = add_forgotten_candidate(db_session, 20)
    declining_chat, declining_peer = add_forgotten_candidate(db_session, 21)
    active_chat, active_peer = add_forgotten_candidate(db_session, 22)
    little_chat, little_peer = add_forgotten_candidate(db_session, 23)
    add_exchanges(
        db_session,
        20,
        forgotten_chat,
        forgotten_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_exchanges(
        db_session,
        21,
        declining_chat,
        declining_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_exchanges(
        db_session,
        22,
        active_chat,
        active_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_exchanges(
        db_session,
        21,
        declining_chat,
        declining_peer,
        [
            FORGOTTEN_AS_OF - timedelta(days=80),
            FORGOTTEN_AS_OF - timedelta(days=60),
            FORGOTTEN_AS_OF - timedelta(days=30),
        ],
        exchanges_per_day=1,
        message_id_start=100,
    )
    add_exchanges(
        db_session,
        22,
        active_chat,
        active_peer,
        [
            datetime(2026, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            FORGOTTEN_AS_OF - timedelta(days=2),
        ],
        exchanges_per_day=5,
        message_id_start=100,
    )
    add_exchanges(
        db_session,
        23,
        little_chat,
        little_peer,
        [
            datetime(2025, 6, 1, tzinfo=timezone.utc),
            datetime(2025, 7, 1, tzinfo=timezone.utc),
        ],
        exchanges_per_day=1,
    )

    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    by_id = {contact.contact_id: contact for contact in result.contacts}

    assert [contact.contact_id for contact in result.contacts] == [20, 21, 22, 23]
    assert by_id[20].classification == "inactive"
    assert by_id[20].evidence_status == "reliable_baseline"
    assert by_id[20].historical_message_count == 50
    assert by_id[20].recent_message_count == 0
    assert by_id[20].days_since_last_communication == 132
    assert by_id[20].activity_decline_percentage == 100
    assert by_id[20].ranking_score is not None

    assert by_id[21].classification == "activity_declined"
    assert 0 < by_id[21].recent_message_count < by_id[21].historical_message_count
    assert by_id[21].activity_decline_percentage is not None
    assert by_id[21].activity_decline_percentage >= 50
    assert by_id[22].classification == "active"
    assert by_id[22].recent_message_count > 0
    assert by_id[22].activity_decline_percentage == 0
    assert by_id[23].classification == "insufficient_data"
    assert by_id[23].ranking_score is None

    assert result.summary.source_account_count == 1
    assert result.summary.eligible_contacts == 4
    assert result.summary.meaningful_historical_contacts == 3
    assert result.summary.currently_inactive_contacts == 2
    assert result.summary.declining_activity_contacts == 2
    assert result.summary.insufficient_data_contacts == 1


def test_forgotten_contacts_excludes_service_and_counts_normalized_text(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    next_message_id = add_exchanges(
        db_session,
        20,
        chat_id,
        peer_id,
        HISTORICAL_ACTIVITY_DATES,
        owner_text="é😀",
        contact_text="x ",
    )
    add_message(
        db_session,
        20 * 10_000 + next_message_id,
        chat_id,
        "message",
        "user-owner",
        is_outgoing=True,
        text_content="",
    )
    add_message(
        db_session,
        20 * 10_000 + next_message_id + 1,
        chat_id,
        "service",
        "user-owner",
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=True,
        text_content="service text must not contribute",
    )
    add_message(
        db_session,
        20 * 10_000 + next_message_id + 2,
        chat_id,
        "service",
        peer_id,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=False,
        text_content="service text must not contribute",
    )

    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    contact = result.contacts[0]

    assert contact.owner_message_count == 26
    assert contact.contact_message_count == 25
    assert contact.historical_message_count == 50
    assert contact.owner_text_length == 25 * len("é😀")
    assert contact.contact_text_length == 25 * len("x ")
    assert contact.total_text_length == 100


def test_forgotten_contacts_marks_ambiguous_direction_unscored(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    add_exchanges(
        db_session,
        20,
        chat_id,
        peer_id,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_message(
        db_session,
        20 * 10_000 + 100,
        chat_id,
        "message",
        peer_id,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=None,
    )
    add_message(
        db_session,
        20 * 10_000 + 101,
        chat_id,
        "message",
        None,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=None,
    )

    contact = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    ).contacts[0]

    assert contact.excluded_ambiguous_message_count == 2
    assert contact.evidence_status == "ambiguous_direction"
    assert contact.classification == "insufficient_data"
    assert contact.ranking_score is None
    assert contact.activity_decline_percentage is None


def test_forgotten_contacts_requires_long_enough_baseline(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    dates = [
        datetime(2026, 4, 1, tzinfo=timezone.utc),
        datetime(2026, 4, 15, tzinfo=timezone.utc),
        datetime(2026, 5, 1, tzinfo=timezone.utc),
        datetime(2026, 5, 15, tzinfo=timezone.utc),
        datetime(2026, 6, 1, tzinfo=timezone.utc),
    ]
    add_exchanges(db_session, 20, chat_id, peer_id, dates, exchanges_per_day=10)

    contact = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    ).contacts[0]

    assert contact.historical_message_count == 100
    assert contact.historical_active_days == 5
    assert contact.historical_active_month_count == 3
    assert contact.evidence_status == "insufficient_baseline"
    assert contact.activity_decline_percentage is None
    assert contact.ranking_score is None


def test_forgotten_contacts_splits_partial_cutoff_month_and_orders_ties(db_session):
    add_account(db_session, 1, "user-owner")
    first_chat, first_peer = add_forgotten_candidate(db_session, 20, name="Zed")
    second_chat, second_peer = add_forgotten_candidate(db_session, 21, name="Alex")
    dates = HISTORICAL_ACTIVITY_DATES + [
        datetime(2026, 7, 10, tzinfo=timezone.utc),
    ]
    add_exchanges(db_session, 20, first_chat, first_peer, dates)
    add_exchanges(db_session, 21, second_chat, second_peer, dates)
    for contact_id, chat_id, peer_id in (
        (20, first_chat, first_peer),
        (21, second_chat, second_peer),
    ):
        add_exchanges(
            db_session,
            contact_id,
            chat_id,
            peer_id,
            [datetime(2026, 7, 25, tzinfo=timezone.utc)],
            exchanges_per_day=1,
            message_id_start=100,
        )

    full_result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
        sort_by="historical_message_count",
    )
    limited_result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
        limit=1,
    )
    first = next(c for c in full_result.contacts if c.contact_id == 20)

    assert [contact.contact_id for contact in full_result.contacts] == [20, 21]
    assert [activity.month for activity in first.historical_activity_by_month][-1] == "2026-07"
    assert first.historical_activity_by_month[-1].total_message_count == 10
    assert first.recent_activity_by_month[0].month == "2026-07"
    assert first.recent_activity_by_month[0].total_message_count == 2
    assert limited_result.summary.eligible_contacts == 2
    assert [contact.contact_id for contact in limited_result.contacts] == [20]


def test_forgotten_contacts_does_not_use_missing_timestamps_as_baseline(db_session):
    add_account(db_session, 1, "user-owner")
    chat_id, peer_id = add_forgotten_candidate(db_session, 20)
    add_exchanges(
        db_session,
        20,
        chat_id,
        peer_id,
        [None],
        exchanges_per_day=1,
    )

    contact = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    ).contacts[0]

    assert contact.total_message_count == 2
    assert contact.first_message_at is None
    assert contact.last_message_at is None
    assert contact.days_since_last_communication is None
    assert contact.historical_message_count == 0
    assert contact.evidence_status == "insufficient_history"
    assert contact.classification == "insufficient_data"
    assert contact.ranking_score is None


def test_forgotten_contacts_excludes_groups_and_multiple_peer_chats(db_session):
    add_account(db_session, 1, "user-owner")
    group_chat, group_peer = add_forgotten_candidate(
        db_session,
        20,
        chat_type="supergroup",
    )
    add_exchanges(
        db_session,
        20,
        group_chat,
        group_peer,
        HISTORICAL_ACTIVITY_DATES,
    )

    chat_id, peer_id = add_forgotten_candidate(db_session, 21)
    third_peer_id = "user-third-peer"
    add_contact(db_session, 31, 1, third_peer_id, "Third peer")
    add_exchanges(
        db_session,
        21,
        chat_id,
        peer_id,
        HISTORICAL_ACTIVITY_DATES,
    )
    add_message(
        db_session,
        21 * 10_000 + 100,
        chat_id,
        "message",
        third_peer_id,
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=False,
        sender_contact_id=31,
    )

    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )

    assert result.summary.eligible_contacts == 0
    assert result.contacts == []


def test_forgotten_contacts_combines_owner_aliases_and_canonical_contacts(db_session):
    add_account(db_session, 1, "user-owner-one", username="anton")
    add_account(db_session, 2, "user-owner-two", username="anton_old")
    for account_id, contact_id in ((1, 20), (2, 30)):
        chat_id, peer_id = add_forgotten_candidate(
            db_session,
            contact_id,
            account_id=account_id,
            peer_id="user-shared-telegram-peer",
        )
        add_exchanges(
            db_session,
            contact_id,
            chat_id,
            peer_id,
            HISTORICAL_ACTIVITY_DATES,
            owner_id=f"user-owner-{'one' if account_id == 1 else 'two'}",
        )

    add_message(
        db_session,
        200051,
        10020,
        "message",
        "user-owner-two",
        message_date=HISTORICAL_ACTIVITY_DATES[0],
        is_outgoing=False,
    )
    result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    assert len(result.contacts) == 1
    assert result.contacts[0].total_message_count == 101
    assert result.contacts[0].owner_message_count == 51
    assert result.contacts[0].contact_message_count == 50
    assert result.contacts[0].source_account_ids == [1, 2]
    assert result.contacts[0].source_account_labels == ["@anton", "@anton_old"]
    assert result.contacts[0].source_contact_ids == [20, 30]
    assert result.contacts[0].account_id is None
    assert result.summary.source_account_count == 2
    assert result.summary.scope == "combined_owner"


def test_forgotten_contacts_empty_database_and_account_without_private_chats(
    db_session,
):
    empty_result = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    assert empty_result.summary.source_account_count == 0
    assert empty_result.summary.eligible_contacts == 0
    assert empty_result.contacts == []

    add_account(db_session, 1, "user-owner")
    group_chat, group_peer = add_forgotten_candidate(
        db_session,
        20,
        chat_type="group",
    )
    add_exchanges(
        db_session,
        20,
        group_chat,
        group_peer,
        HISTORICAL_ACTIVITY_DATES,
    )
    no_private_results = build_forgotten_contacts_statistics(
        db_session,
        as_of=FORGOTTEN_AS_OF,
    )
    assert no_private_results.summary.source_account_count == 1
    assert no_private_results.summary.eligible_contacts == 0
    assert no_private_results.contacts == []