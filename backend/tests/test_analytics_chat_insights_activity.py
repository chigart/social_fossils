from datetime import datetime, timezone

from sqlalchemy import text

from app.routers.analytics_chat_insights import get_chat_insights
from app.schemas.analytics import ChatInsightsResponse
from analytics_test_helpers import add_account, add_chat, add_message


def test_conversation_metrics_keep_undated_and_unknown_senders_unattributed(
    db_session,
):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    add_message(
        db_session, 1, 10, "message", None,
        message_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    add_message(db_session, 2, 10, "message", "user200", message_date=None)

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))
    activity = result.chats[0].conversation_activity

    assert activity.session_count == 1
    assert activity.messages_without_timestamp_count == 1
    assert activity.sender_transition_count == 0
    assert activity.opening_senders[0].sender_id is None
    assert activity.opening_senders[0].display_name == "Unknown sender"


def test_chat_insights_include_average_activity_times_and_calendar_patterns(
    db_session,
):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    dated_messages = [
        (1, "user-a", datetime(2025, 1, 6, 18, 42, tzinfo=timezone.utc)),
        (2, "user-a", datetime(2025, 1, 8, 18, 44, tzinfo=timezone.utc)),
        (3, "user-b", datetime(2025, 2, 4, 18, 42, tzinfo=timezone.utc)),
        (4, "user-b", datetime(2025, 2, 6, 18, 44, tzinfo=timezone.utc)),
    ]
    for message_id, sender_id, message_date in dated_messages:
        add_message(
            db_session, message_id, 10, "message", sender_id,
            message_date=message_date,
        )
    add_message(
        db_session, 5, 10, "service", "user-a",
        message_date=datetime(2025, 2, 9, 12, tzinfo=timezone.utc),
    )
    add_message(db_session, 6, 10, "message", "user-a", message_date=None)

    chat = ChatInsightsResponse.model_validate(
        get_chat_insights(db_session)
    ).chats[0]

    assert chat.average_activity_time == "18:43"
    assert {
        sender.sender_id: sender.average_activity_time
        for sender in chat.senders
    } == {"user-a": "18:43", "user-b": "18:43"}
    assert [(item.period, item.count) for item in chat.weekday_activity] == [
        ("Monday", 1), ("Tuesday", 1), ("Wednesday", 1), ("Thursday", 1),
        ("Friday", 0), ("Saturday", 0), ("Sunday", 0),
    ]
    assert [(item.period, item.count) for item in chat.month_activity] == [
        ("January", 2), ("February", 2), ("March", 0), ("April", 0),
        ("May", 0), ("June", 0), ("July", 0), ("August", 0),
        ("September", 0), ("October", 0), ("November", 0), ("December", 0),
    ]


def test_average_activity_time_uses_circular_mean_around_midnight(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    add_message(
        db_session, 1, 10, "message", "user-a",
        message_date=datetime(2025, 1, 1, 23, 59, tzinfo=timezone.utc),
    )
    add_message(
        db_session, 2, 10, "message", "user-a",
        message_date=datetime(2025, 1, 2, 0, 1, tzinfo=timezone.utc),
    )

    chat = get_chat_insights(db_session).chats[0]

    assert chat.average_activity_time == "00:00"
    assert chat.senders[0].average_activity_time == "00:00"


def test_vk_owner_messages_are_attributed_in_conversation_openers(db_session):
    db_session.execute(
        text(
            "INSERT INTO account "
            "(id, platform, name, platform_user_id) "
            "VALUES (1, 'vk', 'VK owner', 'archive:vk-owner')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO chats "
            "(id, account_id, platform, chat_id, chat_type) "
            "VALUES (10, 1, 'vk', '123', 'personal_chat')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, platform, message_id, sender_id, sender_name, "
            "is_outgoing, message_date, message_type, text_content) "
            "VALUES "
            "(1, 10, 'vk', 'owner-1', 'archive:vk-owner', 'VK owner', TRUE, "
            "'2025-01-01 00:00:00', 'message', 'first'), "
            "(2, 10, 'vk', 'owner-2', 'archive:vk-owner', 'VK owner', TRUE, "
            "'2025-01-01 13:00:00', 'message', 'second'), "
            "(3, 10, 'vk', 'owner-3', 'archive:vk-owner', 'VK owner', TRUE, "
            "'2025-01-02 02:00:00', 'message', 'third')"
        )
    )

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))
    activity = result.chats[0].conversation_activity

    assert [
        (sender.sender_id, sender.display_name, sender.count)
        for sender in activity.opening_senders
    ] == [("archive:vk-owner", "VK owner", 3)]
