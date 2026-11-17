from datetime import datetime, timezone

from sqlalchemy import text

from analytics_test_helpers import add_account, add_chat, add_contact, add_message
from app.routers.analytics_contacts import get_contact_statistics
from app.routers.analytics_overview import (
    get_chat_statistics,
)


def test_contact_platform_filters_pages_but_keeps_all_platform_picker_options(
    db_session,
):
    add_account(db_session, 1, "telegram-owner")
    add_account(db_session, 2, "instagram-owner")
    add_contact(db_session, 40, 1, "telegram-peer", "Telegram peer")
    add_contact(db_session, 50, 2, "instagram-peer", "Instagram peer")
    db_session.execute(
        text("UPDATE account SET platform = 'instagram' WHERE id = 2")
    )
    db_session.execute(
        text(
            "UPDATE canonical_identities SET platform = 'instagram' "
            "WHERE platform_user_id = 'instagram-peer'"
        )
    )
    db_session.execute(
        text("UPDATE contacts SET platform = 'instagram' WHERE id = 50")
    )

    telegram_page = get_contact_statistics(db_session, platform="telegram")

    assert [contact.display_name for contact in telegram_page.items] == [
        "Telegram peer",
    ]
    assert telegram_page.pagination.total == 1
    assert {option.label for option in telegram_page.options} == {
        "Telegram peer",
        "Instagram peer",
    }


def test_chat_and_contact_statistics_support_message_based_sorting(db_session):
    add_account(db_session, 1, "user-owner")
    add_contact(db_session, 40, 1, "peer-a", "Peer A")
    add_contact(db_session, 50, 1, "peer-b", "Peer B")
    add_chat(db_session, 10, 1, "dm-10", "DM", chat_type="personal_chat")
    add_chat(db_session, 20, 1, "group-20", "Group", chat_type="private_group")
    add_chat(db_session, 30, 1, "empty-30", "Empty", chat_type="private_group")

    january = datetime(2025, 1, 1, tzinfo=timezone.utc)
    february = datetime(2025, 2, 1, tzinfo=timezone.utc)
    march = datetime(2025, 3, 1, tzinfo=timezone.utc)
    april = datetime(2025, 4, 1, tzinfo=timezone.utc)
    add_message(
        db_session, 1, 10, "message", "peer-a", january,
        is_outgoing=False, sender_contact_id=40,
    )
    add_message(
        db_session, 2, 10, "message", "peer-a", february,
        is_outgoing=False, sender_contact_id=40,
    )
    add_message(
        db_session, 3, 10, "message", "peer-b", march,
        is_outgoing=False, sender_contact_id=50,
    )
    add_message(
        db_session, 4, 20, "message", "peer-a", february,
        is_outgoing=False, sender_contact_id=40,
    )
    for message_id in range(5, 8):
        add_message(
            db_session, message_id, 20, "message", "peer-b", april,
            is_outgoing=False, sender_contact_id=50,
        )

    chats_by_senders = get_chat_statistics(
        db_session,
        sort_by="distinct_identified_senders",
        sort_direction="asc",
    )
    chats_by_first_message = get_chat_statistics(
        db_session,
        sort_by="earliest_message_timestamp",
        sort_direction="asc",
    )
    chats_by_latest_message = get_chat_statistics(
        db_session,
        sort_by="latest_message_timestamp",
        sort_direction="desc",
    )
    contacts_by_dm_messages = get_contact_statistics(
        db_session,
        sort_by="personal_chat_messages_sent",
        sort_direction="asc",
    )
    contacts_by_group_messages = get_contact_statistics(
        db_session,
        sort_by="group_chat_messages_sent",
        sort_direction="desc",
    )

    assert [chat.chat_id for chat in chats_by_senders.items] == [30, 10, 20]
    assert [chat.chat_id for chat in chats_by_first_message.items] == [10, 20, 30]
    assert [chat.chat_id for chat in chats_by_latest_message.items] == [20, 10, 30]
    assert [contact.display_name for contact in contacts_by_dm_messages.items] == [
        "Peer B",
        "Peer A",
    ]
    assert [
        contact.display_name for contact in contacts_by_group_messages.items
    ] == ["Peer B", "Peer A"]


def test_contact_options_exclude_hidden_contacts_and_keep_original_indices(
    db_session,
):
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
