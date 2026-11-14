from datetime import datetime, timezone

from sqlalchemy import text

from analytics_test_helpers import add_account, add_chat, add_contact, add_message
from app.routers.analytics_communication_balance import get_communication_balance
from app.routers.analytics_communication_timeline_queries import (
    build_communication_timeline_statistics,
)
from app.routers.analytics_overview import get_contact_statistics
from app.schemas.analytics import CommunicationBalanceStatistics


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
