from collections import Counter

from app.analytics_stop_words import STOP_WORDS
from app.routers.analytics_chat_insights import (
    _rank_words,
    extract_emojis,
    get_chat_insights,
)
from app.schemas.analytics import ChatInsightsResponse
from analytics_test_helpers import add_account, add_chat, add_message
from app.main import app


def test_stop_words_exclude_personal_pronouns_but_keep_meaningful_words():
    personal_pronouns = {
        "меня", "мне", "мной", "мною", "тебе", "тебя", "тобой", "тобою",
        "нас", "нам", "нами", "me", "you", "us", "them",
    }
    meaningful_words = {
        "пусть", "пускай", "сегодня", "неужели", "однако", "исключительно",
        "просто", "прямо", "именно",
    }

    assert personal_pronouns <= STOP_WORDS
    assert not meaningful_words & STOP_WORDS
    assert {item.word for item in _rank_words(Counter(personal_pronouns | meaningful_words))} == (
        meaningful_words
    )


def test_extract_emojis_preserves_combined_sequences():
    assert extract_emojis("❤️ 👩‍💻 🇷🇺 3️⃣ 💔") == [
        "❤️",
        "👩‍💻",
        "🇷🇺",
        "3️⃣",
        "💔",
    ]


def test_popular_words_exclude_common_english_and_russian_words(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    add_message(
        db_session,
        1,
        10,
        "message",
        "user100",
        text_content=(
            "не НЕ и я в а что это на ты с the AND is not for on by we "
            "important thing важный нечто"
        ),
    )

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))
    chat = result.chats[0]
    sender = chat.senders[0]

    excluded_words = {
        "не", "и", "я", "в", "а", "что", "это", "на", "ты", "с",
        "the", "and", "is", "not", "for", "on", "by", "we",
    }
    assert {item.word for item in chat.popular_words}.isdisjoint(excluded_words)
    assert {item.word for item in sender.popular_words}.isdisjoint(excluded_words)
    assert {item.word for item in chat.popular_words} == {
        "важный",
        "нечто",
        "important",
        "thing",
    }
    assert chat.ordinary_message_count == 1
    assert chat.text_length == len(
        "не НЕ и я в а что это на ты с the AND is not for on by we "
        "important thing важный нечто"
    )


def test_chat_insights_include_requested_chat_types_and_exclude_service_messages(
    db_session,
):
    add_account(db_session, 1, "user-owner", name="Owner", username="owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    add_chat(db_session, 11, 1, "chat-11", "Group", chat_type="private_group")
    add_chat(
        db_session,
        12,
        1,
        "chat-12",
        "Supergroup",
        chat_type="private_supergroup",
    )
    add_chat(db_session, 13, 1, "chat-13", "Unsupported", chat_type="group")

    add_message(
        db_session,
        1,
        10,
        "message",
        "user100",
        text_content="Hello hello ❤️ 👩‍💻",
        raw_payload={
            "reactions": [
                {
                    "type": "emoji",
                    "count": 4,
                    "emoji": "💔",
                    "recent": [{"from": "Lena", "from_id": "user200"}],
                },
                {
                    "type": "emoji",
                    "count": 1,
                    "emoji": "👍",
                    "recent": [{"from": "Lena", "from_id": "user200"}],
                },
            ]
        },
    )
    add_message(
        db_session,
        2,
        10,
        "message",
        "user100",
        text_content="hello world",
    )
    add_message(
        db_session,
        3,
        10,
        "service",
        "user100",
        text_content="service hello",
        raw_payload={
            "reactions": [
                {
                    "type": "emoji",
                    "count": 99,
                    "emoji": "🔥",
                    "recent": [{"from": "Lena", "from_id": "user200"}],
                }
            ]
        },
    )
    add_message(
        db_session,
        4,
        11,
        "message",
        "user200",
        text_content="Group group 🎉",
    )
    add_message(
        db_session,
        5,
        12,
        "message",
        "user300",
        text_content="Supergroup message 🙂",
    )
    add_message(
        db_session,
        6,
        13,
        "message",
        "user400",
        text_content="Not included 🚫",
    )

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))

    assert [chat.title for chat in result.chats] == ["Direct", "Group", "Supergroup"]
    direct = result.chats[0]
    assert direct.ordinary_message_count == 2
    assert direct.text_length == len("Hello hello ❤️ 👩‍💻hello world")
    assert direct.popular_words[0].word == "hello"
    assert direct.popular_words[0].count == 3
    assert direct.popular_emojis[0].emoji == "❤️"
    assert {sender.sender_telegram_id: sender.message_count for sender in direct.senders} == {
        "user100": 2
    }
    assert direct.reaction_count == 5
    assert [(item.emoji, item.count) for item in direct.reaction_emojis] == [
        ("💔", 4),
        ("👍", 1),
    ]
    assert direct.reactors[0].reactor_telegram_id == "user200"
    assert direct.reactors[0].reaction_count == 2
    assert direct.reactors[0].popular_emojis[0].emoji == "👍"
    pair = direct.reactor_author_pairs[0]
    assert pair.reactor_name == "Lena"
    assert pair.author_name == "user100"
    assert pair.observed_reaction_count == 2
    assert pair.messages_with_observed_reaction_count == 1
    assert pair.author_message_count == 2
    assert pair.observed_message_percentage == 50
    assert result.chats[1].popular_words[0].word == "group"
    assert result.chats[2].popular_emojis[0].emoji == "🙂"
    assert "/api/analytics/chat-insights" in app.openapi()["paths"]


def test_empty_supported_chat_and_unattributed_reactions_are_safe(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 9, 1, "no-messages", "No messages", chat_type="private_group")
    add_chat(db_session, 10, 1, "empty", "Empty", chat_type="private_group")
    add_message(
        db_session,
        1,
        10,
        "message",
        None,
        text_content=None,
        raw_payload={
            "reactions": [
                {
                    "type": "emoji",
                    "count": 2,
                    "emoji": "😂",
                    "recent": [{"from": "No id"}],
                },
                {"type": "custom_emoji", "count": 100, "emoji": "x"},
                {"type": "emoji", "count": -1, "emoji": "👀"},
            ]
        },
    )

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))

    assert len(result.chats) == 2
    assert result.chats[0].ordinary_message_count == 0
    assert result.chats[0].senders == []
    assert result.chats[1].ordinary_message_count == 1
    assert result.chats[1].text_length == 0
    assert result.chats[1].senders[0].display_name == "Unknown sender"
    assert result.chats[1].reaction_count == 2
    assert result.chats[1].reactors == []
    assert result.chats[1].reactor_author_pairs == []


def test_chat_insights_measure_reply_tempo_sessions_and_media_categories(db_session):
    from datetime import datetime, timedelta, timezone

    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)

    add_message(
        db_session,
        1,
        10,
        "message",
        "user-owner",
        message_date=start,
        text_content="Photo caption",
        raw_payload={"media_type": "photo", "file": "photo.jpg"},
    )
    add_message(
        db_session,
        2,
        10,
        "message",
        "user200",
        message_date=start + timedelta(minutes=5),
        text_content="Reply",
        reply_to_telegram_message_id="1",
    )
    add_message(
        db_session,
        3,
        10,
        "message",
        "user-owner",
        message_date=start + timedelta(minutes=10),
        text_content="Another reply",
        reply_to_telegram_message_id="2",
    )
    add_message(
        db_session,
        4,
        10,
        "message",
        "user200",
        message_date=start + timedelta(hours=12, minutes=10),
        raw_payload={"media_type": "voice_message", "duration_seconds": 8},
    )
    add_message(
        db_session,
        5,
        10,
        "message",
        "user-owner",
        message_date=start + timedelta(hours=12, minutes=15),
        raw_payload={"sticker_emoji": "🙂"},
        reply_to_telegram_message_id="missing",
    )
    add_message(
        db_session,
        6,
        10,
        "service",
        "user200",
        message_date=start + timedelta(hours=12, minutes=16),
        raw_payload={"action": "join_group"},
    )

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))
    chat = result.chats[0]

    assert chat.reply_tempo.reply_reference_count == 3
    assert chat.reply_tempo.measured_reply_count == 2
    assert chat.reply_tempo.median_response_seconds == 300
    assert chat.conversation_activity.session_gap_hours == 12
    assert chat.conversation_activity.session_count == 2
    assert chat.conversation_activity.sender_transition_count == 3
    assert chat.conversation_activity.sender_switch_count == 3
    assert chat.conversation_activity.sender_switch_percentage == 100
    assert chat.conversation_activity.longest_turn_taking_streak == 3
    assert {
        (sender.sender_telegram_id, sender.count)
        for sender in chat.conversation_activity.opening_senders
    } == {("user-owner", 1), ("user200", 1)}
    assert chat.conversation_activity.attributed_handoff_count == 1
    assert chat.conversation_activity.unattributed_handoff_count == 0
    handoff = chat.conversation_activity.handoffs[0]
    assert (handoff.previous_closer_id, handoff.next_opener_id, handoff.count) == (
        "user-owner",
        "user200",
        1,
    )
    assert [(item.category, item.count) for item in chat.message_type_breakdown] == [
        ("Text", 2),
        ("Photo", 1),
        ("Service event", 1),
        ("Sticker", 1),
        ("Voice message", 1),
    ]
    photo = next(item for item in chat.message_type_breakdown if item.category == "Photo")
    assert photo.with_text_count == 1


def test_conversation_metrics_keep_undated_and_unknown_senders_unattributed(db_session):
    from datetime import datetime, timezone

    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    add_message(
        db_session,
        1,
        10,
        "message",
        None,
        message_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    add_message(db_session, 2, 10, "message", "user200", message_date=None)

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))
    activity = result.chats[0].conversation_activity

    assert activity.session_count == 1
    assert activity.messages_without_timestamp_count == 1
    assert activity.sender_transition_count == 0
    assert activity.opening_senders[0].sender_telegram_id is None
    assert activity.opening_senders[0].display_name == "Unknown sender"
