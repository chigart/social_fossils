from datetime import datetime, timedelta, timezone

from app.routers.analytics_chat_insights import get_chat_insights
from app.routers.analytics_overview import get_chat_statistics
from app.schemas.analytics import ChatInsightsResponse
from analytics_test_helpers import add_account, add_chat, add_message


def test_chat_insights_measure_reply_tempo_sessions_and_media_categories(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)

    add_message(
        db_session, 1, 10, "message", "user-owner",
        message_date=start, is_outgoing=True, text_content="Photo caption",
        raw_payload={"media_type": "photo", "file": "photo.jpg"},
    )
    add_message(
        db_session, 2, 10, "message", "user200",
        message_date=start + timedelta(minutes=5), is_outgoing=False,
        text_content="Reply", reply_to_telegram_message_id="1",
    )
    add_message(
        db_session, 3, 10, "message", "user-owner",
        message_date=start + timedelta(minutes=15), is_outgoing=True,
        text_content="Another reply", reply_to_telegram_message_id="2",
    )
    add_message(
        db_session, 4, 10, "message", "user200",
        message_date=start + timedelta(hours=12, minutes=20),
        is_outgoing=False,
        raw_payload={"media_type": "voice_message", "duration_seconds": 8},
    )
    add_message(
        db_session, 5, 10, "message", "user-owner",
        message_date=start + timedelta(hours=12, minutes=25), is_outgoing=True,
        raw_payload={"sticker_emoji": "🙂"},
        reply_to_telegram_message_id="missing",
    )
    add_message(
        db_session, 6, 10, "message", "user-owner",
        message_date=start + timedelta(hours=12, minutes=26),
        is_outgoing=True, text_content="A second owner response",
    )
    add_message(
        db_session, 7, 10, "service", "user200",
        message_date=start + timedelta(hours=12, minutes=26),
        is_outgoing=False, raw_payload={"action": "join_group"},
    )

    chat = ChatInsightsResponse.model_validate(get_chat_insights(db_session)).chats[0]
    dms_chat = get_chat_statistics(db_session, chat_scope="dm").items[0]

    assert chat.reply_tempo.owner_opened_session_count == 1
    assert chat.reply_tempo.measured_contact_reply_session_count == 1
    assert chat.reply_tempo.message_interval_count == 4
    assert chat.reply_tempo.average_response_seconds is None
    assert chat.reply_tempo.longest_response_seconds == 300
    assert chat.reply_tempo.median_message_interval_seconds == 300
    assert dms_chat.average_response_seconds is None
    assert chat.conversation_activity.session_gap_hours == 12
    assert chat.conversation_activity.session_count == 2
    assert chat.conversation_activity.sender_transition_count == 4
    assert chat.conversation_activity.sender_switch_count == 3
    assert chat.conversation_activity.sender_switch_percentage == 75
    assert chat.conversation_activity.longest_turn_taking_streak == 3
    assert {
        (sender.sender_id, sender.count)
        for sender in chat.conversation_activity.opening_senders
    } == {("user-owner", 1), ("user200", 1)}
    assert chat.conversation_activity.attributed_handoff_count == 1
    assert chat.conversation_activity.unattributed_handoff_count == 0
    handoff = chat.conversation_activity.handoffs[0]
    assert (handoff.previous_closer_id, handoff.next_opener_id, handoff.count) == (
        "user-owner", "user200", 1,
    )
    assert [(item.category, item.count) for item in chat.message_type_breakdown] == [
        ("Text", 3), ("Photo", 1), ("Service event", 1),
        ("Sticker", 1), ("Voice message", 1),
    ]
    photo = next(item for item in chat.message_type_breakdown if item.category == "Photo")
    assert photo.with_text_count == 1
    assert [(sender.display_name, sender.count) for sender in photo.senders] == [
        ("user-owner", 1)
    ]
    assert next(
        item for item in chat.message_type_breakdown if item.category == "Service event"
    ).senders[0].display_name == "user200"
    assert next(
        item for item in chat.message_type_breakdown if item.category == "Text"
    ).senders == []


def test_chat_insights_reply_tempo_uses_first_different_member_within_12_hours(
    db_session,
):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 20, 1, "group-20", "Group", chat_type="private_group")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)

    messages = [
        (1, "member-a", 0, False),
        (2, "member-a", 120, False),
        (3, "member-b", 300, False),
        (4, "user-owner", 600, True),
        (5, "member-c", 13 * 3600, False),
        (6, "member-c", 20 * 3600, False),
        (7, "member-c", 24 * 3600, False),
        (8, "user-owner", int(25.5 * 3600), True),
    ]
    for message_id, sender_id, elapsed_seconds, is_outgoing in messages:
        add_message(
            db_session, message_id, 20, "message", sender_id,
            message_date=start + timedelta(seconds=elapsed_seconds),
            is_outgoing=is_outgoing,
        )

    chat = ChatInsightsResponse.model_validate(
        get_chat_insights(db_session, chat_id=20)
    ).chats[0]

    assert chat.reply_tempo.owner_opened_session_count == 0
    assert chat.reply_tempo.measured_contact_reply_session_count == 0
    assert chat.reply_tempo.message_interval_count == 6
    assert chat.reply_tempo.average_response_seconds is None
    assert chat.reply_tempo.longest_response_seconds is None
    assert chat.reply_tempo.median_message_interval_seconds == 2850


def test_chat_insights_average_requires_five_contact_reply_sessions(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 30, 1, "direct-30", "Direct", chat_type="personal_chat")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(5):
        session_start = start + timedelta(days=index)
        add_message(
            db_session, index * 2 + 1, 30, "message", "user-owner",
            message_date=session_start, is_outgoing=True,
        )
        add_message(
            db_session, index * 2 + 2, 30, "message", "user200",
            message_date=session_start + timedelta(minutes=10), is_outgoing=False,
        )

    chat = ChatInsightsResponse.model_validate(
        get_chat_insights(db_session, chat_id=30)
    ).chats[0]
    dms_chat = get_chat_statistics(db_session, chat_scope="dm").items[0]

    assert chat.reply_tempo.measured_contact_reply_session_count == 5
    assert chat.reply_tempo.average_response_seconds == 600
    assert chat.reply_tempo.average_response_seconds == dms_chat.average_response_seconds
