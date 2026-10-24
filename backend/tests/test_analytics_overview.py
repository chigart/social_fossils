from datetime import datetime, timezone

from sqlalchemy import text

from analytics_test_helpers import (
    add_account,
    add_chat,
    add_contact,
    add_message,
)

from app.main import app
from app.routers.analytics_communication_balance import get_communication_balance
from app.routers.analytics_chat_insights import get_chat_insights
from app.routers.analytics_overview import (
    get_chat_statistics,
    get_contact_statistics,
    get_overview,
)
from app.routers.analytics_communication_timeline_queries import (
    build_communication_timeline_statistics,
)
from app.routers.analytics_forgotten_contacts import (
    build_forgotten_contacts_statistics,
)
from app.schemas.analytics import (
    ChatStatistics,
    CommunicationBalanceStatistics,
    ContactStatistics,
    OverviewStatistics,
)


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


def test_instagram_records_are_excluded_from_telegram_analytics(db_session):
    db_session.execute(
        text(
            "INSERT INTO account "
            "(id, platform, name, platform_user_id) "
            "VALUES (2, 'instagram', 'Instagram account', NULL)"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO chats "
            "(id, account_id, platform, chat_id, chat_type, title) "
            "VALUES (20, 2, 'instagram', 'inbox/thread_20', 'personal_chat', 'Thread')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, platform, source_record_key, sender_name, "
            "message_type, text_content, raw_payload) "
            "VALUES (20, 20, 'instagram', 'record-key', 'Friend', "
            "'message', 'synthetic', '{}')"
        )
    )

    overview = get_overview(db_session)
    timeline = build_communication_timeline_statistics(db_session)
    forgotten = build_forgotten_contacts_statistics(db_session)
    balance = get_communication_balance(db_session)

    assert overview.total_imported_accounts == 0
    assert overview.total_chats == 0
    assert overview.total_messages == 0
    assert get_chat_statistics(db_session) == []
    assert get_contact_statistics(db_session) == []
    assert balance.contacts == []
    assert get_chat_insights(db_session).chats == []
    assert timeline.summary.ordinary_message_count == 0
    assert forgotten.summary.source_account_count == 0

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
