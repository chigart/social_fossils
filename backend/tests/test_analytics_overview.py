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
        "imported_accounts": [],
        "earliest_message_timestamp": None,
        "latest_message_timestamp": None,
    }
    assert get_chat_statistics(db_session).items == []
    assert get_contact_statistics(db_session).items == []
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


def test_chat_and_contact_pages_are_bounded_and_keep_all_picker_options(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "First")
    add_chat(db_session, 20, 1, "chat-20", "Second")
    add_chat(db_session, 30, 1, "chat-30", "Third")
    add_contact(db_session, 40, 1, "peer-1", "Ada")
    add_contact(db_session, 50, 1, "peer-2", "Bea")
    add_contact(db_session, 60, 1, "peer-3", "Cleo")

    chat_page = get_chat_statistics(db_session, page=2, page_size=1)
    contact_page = get_contact_statistics(db_session, page=2, page_size=1)

    assert [chat.chat_id for chat in chat_page.items] == [20]
    assert chat_page.pagination.total == 3
    assert len(chat_page.options) == 3
    assert [contact.display_name for contact in contact_page.items] == ["Bea"]
    assert contact_page.pagination.total == 3
    assert len(contact_page.options) == 3


def test_chat_scope_filters_pages_and_options(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "dm-10", "First DM", chat_type="personal_chat")
    add_chat(db_session, 20, 1, "group-20", "Group", chat_type="private_group")
    add_chat(db_session, 30, 1, "other-30", "Other", chat_type="channel")

    dm_page = get_chat_statistics(db_session, chat_scope="dm")
    group_page = get_chat_statistics(db_session, chat_scope="group", page_size=1)

    assert [chat.title for chat in dm_page.items] == ["First DM"]
    assert dm_page.pagination.total == 1
    assert [option.label for option in dm_page.options] == ["First DM"]
    assert [chat.title for chat in group_page.items] == ["Group"]
    assert group_page.pagination.total == 2
    assert [option.label for option in group_page.options] == ["Group", "Other"]


def test_contact_options_exclude_hidden_contacts_and_keep_original_indices(db_session):
    add_account(db_session, 1, "user-owner")
    add_contact(db_session, 40, 1, "peer-1", "Ada")
    add_contact(db_session, 50, 1, "peer-2", "Bea")
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(id, account_id, platform, platform_user_id, display_name) "
            "VALUES (60, 1, 'telegram', NULL, '   ')"
        )
    )

    result = get_contact_statistics(db_session)

    assert [option.value for option in result.options] == ["1", "2"]
    assert [option.label for option in result.options] == ["Ada", "Bea"]


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
    chats = get_chat_statistics(db_session).items

    assert overview.total_imported_accounts == 1
    assert overview.total_chats == 1
    assert overview.total_messages == 0
    assert [
        account.model_dump() for account in overview.imported_accounts
    ] == [
        {
            "id": 1,
            "platform": "telegram",
            "name": "Ant Malkov",
            "username": "anton",
            "platform_user_id": "user-owner",
            "total_messages": 0,
            "total_contacts": 0,
        }
    ]
    assert overview.earliest_message_timestamp is None
    assert len(chats) == 1
    assert ChatStatistics.model_validate(chats[0]).model_dump() == {
        "chat_id": 10,
        "account_id": 1,
        "platform": "telegram",
        "source_account_label": "@anton",
        "platform_chat_id": "telegram-chat-10",
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
    add_chat(
        db_session, 10, 1, "telegram-chat-10", "Active", chat_type="personal_chat"
    )
    add_chat(
        db_session, 11, 1, "telegram-chat-11", "Second", chat_type="private_group"
    )
    add_chat(db_session, 12, 1, "telegram-chat-12", "Empty")
    db_session.execute(
        text(
            "INSERT INTO contacts (id, account_id, platform_user_id, display_name) "
            "VALUES (20, 1, 'user-alex', 'Alex'), (21, 1, 'user-sam', 'Sam')"
        )
    )

    first_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    second_date = datetime(2025, 1, 2, tzinfo=timezone.utc)
    latest_date = datetime(2025, 1, 5, tzinfo=timezone.utc)
    add_message(db_session, 1, 10, "message", "user-alex", first_date, is_outgoing=False, sender_contact_id=20)
    add_message(db_session, 2, 10, "service", "user-sam", is_outgoing=False, sender_contact_id=21)
    add_message(db_session, 3, 10, "message", None, second_date, is_outgoing=False)
    add_message(db_session, 4, 10, "message", "user-owner", is_outgoing=True)
    add_message(db_session, 5, 10, "service", "user-unlinked", latest_date, is_outgoing=False)
    add_message(db_session, 6, 11, "message", "user-alex", second_date, is_outgoing=False)

    overview = OverviewStatistics.model_validate(get_overview(db_session))
    chats = [
        ChatStatistics.model_validate(chat)
        for chat in get_chat_statistics(db_session).items
    ]
    contacts = [
        ContactStatistics.model_validate(contact)
        for contact in get_contact_statistics(db_session).items
    ]

    assert overview.total_imported_accounts == 1
    assert overview.total_chats == 3
    assert overview.total_messages == 6
    assert overview.total_ordinary_messages == 4
    assert overview.total_service_messages == 2
    assert [
        account.model_dump() for account in overview.imported_accounts
    ] == [
        {
            "id": 1,
            "platform": "telegram",
            "name": "Account 1",
            "username": None,
            "platform_user_id": "user-owner",
            "total_messages": 6,
            "total_contacts": 2,
        }
    ]
    assert overview.earliest_message_timestamp == first_date
    assert overview.latest_message_timestamp == latest_date

    by_chat_id = {chat.chat_id: chat for chat in chats}
    assert by_chat_id[10].platform_chat_id == "telegram-chat-10"
    assert by_chat_id[10].total_messages == 5
    assert by_chat_id[10].ordinary_messages == 3
    assert by_chat_id[10].service_messages == 2
    assert by_chat_id[10].distinct_identified_senders == 4
    assert by_chat_id[11].total_messages == 1
    assert by_chat_id[11].distinct_identified_senders == 1
    assert by_chat_id[12].total_messages == 0

    by_sender = {
        contact.platform_user_ids[0] if contact.platform_user_ids else None: contact
        for contact in contacts
    }
    assert set(by_sender) == {"user-alex", "user-sam", "user-unlinked", None}
    assert "contact_id" not in by_sender["user-alex"].model_dump()
    assert by_sender["user-alex"].source_contact_ids == [20]
    assert by_sender["user-alex"].total_messages_sent == 2
    assert by_sender["user-alex"].personal_chat_messages_sent == 1
    assert by_sender["user-alex"].group_chat_messages_sent == 1
    assert by_sender["user-alex"].ordinary_messages_sent == 2
    assert by_sender["user-sam"].service_events_attributed == 1
    assert by_sender["user-sam"].personal_chat_messages_sent == 1
    assert by_sender["user-sam"].group_chat_messages_sent == 0
    assert by_sender["user-unlinked"].source_contact_ids == []
    assert by_sender["user-unlinked"].service_events_attributed == 1
    assert by_sender[None].total_messages_sent == 1
    assert by_sender[None].personal_chat_messages_sent == 1
    assert by_sender[None].group_chat_messages_sent == 0

def test_nonstandard_message_type_only_contributes_to_total(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "telegram-chat-10")
    add_message(db_session, 1, 10, "unknown_event", "user-other", is_outgoing=False)

    overview = get_overview(db_session)
    contact = get_contact_statistics(db_session).items[0]

    assert overview.total_messages == 1
    assert overview.total_ordinary_messages == 0
    assert overview.total_service_messages == 0
    assert contact.total_messages_sent == 1
    assert contact.ordinary_messages_sent == 0
    assert contact.service_events_attributed == 0


def test_unidentified_sender_is_not_multiplied_by_idless_contacts(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10")
    db_session.execute(
        text(
            "INSERT INTO contacts (id, account_id, display_name) "
            "VALUES (20, 1, 'Address-book entry one'), "
            "(21, 1, 'Address-book entry two')"
        )
    )
    add_message(
        db_session,
        1,
        10,
        "message",
        None,
        is_outgoing=False,
    )

    contacts = get_contact_statistics(db_session).items

    assert sum(contact.total_messages_sent for contact in contacts) == 1
    assert len([contact for contact in contacts if contact.source_contact_ids]) == 2


def test_instagram_records_are_included_in_unified_analytics(db_session):
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
            "INSERT INTO canonical_identities "
            "(id, platform, platform_user_id) "
            "VALUES (20, 'instagram', 'instagram-peer')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(id, account_id, platform, platform_user_id, canonical_identity_id, "
            "display_name, source_contact_key) "
            "VALUES (20, 2, 'instagram', 'instagram-peer', 20, "
            "'Synthetic Instagram peer', NULL)"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(id, account_id, platform, platform_user_id, canonical_identity_id, "
            "display_name, source_contact_key) "
            "VALUES (21, 2, 'instagram', NULL, NULL, "
            "'Synthetic address-book contact', 'contact-source-key')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, platform, source_record_key, sender_id, "
            "sender_contact_id, sender_name, message_type, text_content, raw_payload) "
            "VALUES (20, 20, 'instagram', 'record-key', 'instagram-peer', "
            "20, 'Synthetic Instagram peer', 'message', 'synthetic', '{}')"
        )
    )

    overview = get_overview(db_session)
    timeline = build_communication_timeline_statistics(db_session)
    forgotten = build_forgotten_contacts_statistics(db_session)
    balance = get_communication_balance(db_session)

    assert overview.total_imported_accounts == 1
    assert overview.total_chats == 1
    assert overview.total_messages == 1
    chat = ChatStatistics.model_validate(get_chat_statistics(db_session).items[0])
    assert chat.platform == "instagram"
    instagram_contacts = get_contact_statistics(db_session).items
    assert len(instagram_contacts) == 2
    by_name = {contact.display_name: contact for contact in instagram_contacts}
    assert by_name["Synthetic Instagram peer"].platforms == ["instagram"]
    assert by_name["Synthetic Instagram peer"].platform_user_ids == ["instagram-peer"]
    assert by_name["Synthetic Instagram peer"].total_messages_sent == 0
    assert by_name["Synthetic address-book contact"].source_contact_ids == [21]
    assert by_name["Synthetic address-book contact"].total_messages_sent == 0
    assert balance.contacts == []
    chat_insight = get_chat_insights(db_session).chats[0]
    assert chat_insight.platform == "instagram"
    assert chat_insight.ordinary_message_count == 1
    assert chat_insight.senders[0].sender_id == "instagram-peer"
    assert timeline.summary.ordinary_message_count == 1
    assert timeline.summary.unknown_direction_message_count == 1
    assert forgotten.summary.source_account_count == 1


def test_explicitly_linked_contact_aggregates_across_platforms(db_session):
    add_account(db_session, 1, "tg-owner")
    add_chat(db_session, 10, 1, "tg-chat", chat_type="personal_chat")
    add_contact(db_session, 11, 1, "tg-peer", "Shared person")
    telegram_identity_id = db_session.scalar(
        text(
            "SELECT id FROM canonical_identities "
            "WHERE platform = 'telegram' AND platform_user_id = 'tg-peer'"
        )
    )

    db_session.execute(
        text(
            "INSERT INTO account (id, platform, name, platform_user_id) "
            "VALUES (2, 'instagram', 'Instagram account', 'ig-owner')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO chats (id, account_id, platform, chat_id, chat_type) "
            "VALUES (20, 2, 'instagram', 'ig-chat', 'personal_chat')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO canonical_identities "
            "(id, platform, platform_user_id, identity_group_id) "
            "VALUES (20, 'instagram', 'ig-peer', 77)"
        )
    )
    db_session.execute(
        text(
            "UPDATE canonical_identities SET identity_group_id = 77 WHERE id = :id"
        ),
        {"id": telegram_identity_id},
    )
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(id, account_id, platform, platform_user_id, canonical_identity_id, display_name) "
            "VALUES (20, 2, 'instagram', 'ig-peer', 20, 'Shared person')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO canonical_identities "
            "(id, platform, platform_user_id) "
            "VALUES (21, 'instagram', 'tg-owner')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(id, account_id, platform, platform_user_id, canonical_identity_id, display_name) "
            "VALUES (21, 2, 'instagram', 'tg-owner', 21, 'Shared person')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO chats (id, account_id, platform, chat_id, chat_type) "
            "VALUES (21, 2, 'instagram', 'ig-unlinked-chat', 'personal_chat')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, platform, message_id, sender_id, sender_contact_id, "
            "is_outgoing, message_type, text_content, raw_payload) "
            "VALUES (22, 21, 'instagram', '22', 'tg-owner', 21, FALSE, "
            "'message', 'unlinked', '{}')"
        )
    )

    first_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    second_date = datetime(2025, 1, 2, tzinfo=timezone.utc)
    add_message(
        db_session, 1, 10, "message", "tg-owner", first_date,
        is_outgoing=True, text_content="o" * 250,
    )
    add_message(
        db_session, 2, 10, "message", "tg-peer", first_date,
        is_outgoing=False, sender_contact_id=11, text_content="p" * 250,
    )
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, platform, message_id, sender_id, sender_contact_id, "
            "is_outgoing, message_date, message_type, text_content, raw_payload) "
            "VALUES "
            "(20, 20, 'instagram', '20', 'ig-owner', NULL, TRUE, :message_date, "
            "'message', :owner_text, '{}'), "
            "(21, 20, 'instagram', '21', 'ig-peer', 20, FALSE, :message_date, "
            "'message', :peer_text, '{}')"
        ),
        {
            "message_date": second_date,
            "owner_text": "o" * 250,
            "peer_text": "p" * 250,
        },
    )

    all_contacts = get_contact_statistics(db_session).items
    contact = next(
        item
        for item in all_contacts
        if item.identity_group_id == 77
    )
    unlinked_same_name = next(
        item
        for item in all_contacts
        if item.display_name == "Shared person" and item.identity_group_id is None
    )
    timeline = build_communication_timeline_statistics(
        db_session,
        canonical_identity_id=telegram_identity_id,
    )
    balance = CommunicationBalanceStatistics.model_validate(
        get_communication_balance(db_session)
    )

    assert contact.platforms == ["instagram", "telegram"]
    assert contact.platform_user_ids == ["ig-peer", "tg-peer"]
    assert contact.source_account_ids == [1, 2]
    assert [
        (source.platform, source.label) for source in contact.source_accounts
    ] == [("instagram", "Instagram account"), ("telegram", "Account 1")]
    assert contact.total_messages_sent == 2
    assert unlinked_same_name.platforms == ["instagram"]
    assert unlinked_same_name.platform_user_ids == ["tg-owner"]
    assert unlinked_same_name.total_messages_sent == 1
    assert timeline.summary.ordinary_message_count == 4
    assert timeline.summary.owner_message_count == 2
    assert timeline.summary.contact_message_count == 2
    assert timeline.summary.source_account_ids == [1, 2]
    linked_balance = next(
        item for item in balance.contacts if item.identity_group_id == 77
    )
    assert linked_balance.total_message_count == 4
    assert linked_balance.owner_text_length == 500
    assert linked_balance.contact_text_length == 500

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

    add_message(db_session, 1, 10, "message", "user-shared-peer", is_outgoing=False)
    add_message(db_session, 2, 20, "message", "user-shared-peer", is_outgoing=False)
    add_message(db_session, 3, 10, "message", "user-twin-one", is_outgoing=False)
    add_message(db_session, 4, 20, "message", "user-twin-two", is_outgoing=False)
    add_message(db_session, 5, 10, "message", "user-unlinked", is_outgoing=False)
    add_message(db_session, 6, 20, "message", "user-unlinked", is_outgoing=False)
    add_message(
        db_session,
        7,
        10,
        "message",
        "user-owner-two",
        is_outgoing=False,
    )

    contacts = get_contact_statistics(db_session).items
    shared = next(
        contact
        for contact in contacts
        if "user-shared-peer" in contact.platform_user_ids
    )
    twins = [contact for contact in contacts if contact.display_name == "Twin"]
    unlinked = [
        contact
        for contact in contacts
        if "user-unlinked" in contact.platform_user_ids
    ]

    assert shared.total_messages_sent == 2
    assert shared.source_account_ids == [1, 2]
    assert shared.source_account_labels == ["@anton", "Anton Malkov"]
    assert [
        (source.platform, source.label) for source in shared.source_accounts
    ] == [("telegram", "@anton"), ("telegram", "Anton Malkov")]
    assert shared.source_contact_ids == [20, 30]
    assert shared.account_id is None
    assert len(twins) == 2
    assert {contact.platform_user_ids[0] for contact in twins} == {
        "user-twin-one",
        "user-twin-two",
    }
    assert len(unlinked) == 2
    assert {contact.account_id for contact in unlinked} == {1, 2}
    assert all(
        "user-owner-two" not in contact.platform_user_ids for contact in contacts
    )
