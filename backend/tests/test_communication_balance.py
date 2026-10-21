from datetime import datetime, timezone

from analytics_test_helpers import (
    add_account,
    add_chat,
    add_contact,
    add_message,
)

from app.routers.analytics_communication_balance import get_communication_balance
from app.schemas.analytics import CommunicationBalanceStatistics


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
