from collections import Counter
from datetime import datetime, timezone
from sqlalchemy import text

from app.constants import STOP_WORDS
from app.routers.analytics_chat_insights_helpers import _rank_words
from app.routers.analytics_chat_insights import (
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
    assert "message" in STOP_WORDS
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


def test_extract_emojis_skips_plain_text():
    assert extract_emojis("synthetic benchmark text alpha beta 123") == []


def test_chat_insights_returns_one_chat_and_supports_searching_all_chat_options(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "First", chat_type="personal_chat")
    add_chat(db_session, 20, 1, "chat-20", "Second", chat_type="private_group")
    add_message(db_session, 1, 10, "message", "peer-10", text_content="first words")
    add_message(db_session, 2, 20, "message", "peer-20", text_content="second words")

    default_chat = get_chat_insights(db_session)
    selected_chat = get_chat_insights(db_session, chat_id=10)

    assert [chat.chat_id for chat in default_chat.chats] == [10]
    assert [option.value for option in default_chat.options] == ["10", "20"]
    assert [chat.chat_id for chat in selected_chat.chats] == [10]
    assert [option.value for option in selected_chat.options] == ["10", "20"]
    parameter_names = [
        parameter["name"]
        for parameter in app.openapi()["paths"]["/api/analytics/chat-insights"][
            "get"
        ]["parameters"]
    ]
    assert parameter_names == ["chat_id"]


def test_instagram_group_insights_separate_senders_without_platform_ids(db_session):
    db_session.execute(
        text(
            "INSERT INTO account (id, platform, name, platform_user_id) "
            "VALUES (1, 'instagram', 'Instagram owner', 'user-owner')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO chats "
            "(id, account_id, platform, chat_id, title, chat_type) "
            "VALUES (10, 1, 'instagram', 'tonsai', 'Tonsai', 'private_group')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, platform, message_id, sender_id, sender_name, "
            "message_type, text_content, raw_payload) "
            "VALUES (:id, 10, 'instagram', :message_id, NULL, :sender_name, "
            "'message', 'synthetic text', '{}')"
        ),
        [
            {
                "id": index,
                "message_id": str(index),
                "sender_name": "Kent Pat" if index <= 5 else "Anton Malkov",
            }
            for index in range(1, 7)
        ],
    )

    result = get_chat_insights(db_session, chat_id=10)

    assert [
        (sender.sender_id, sender.display_name, sender.message_count)
        for sender in result.chats[0].senders
    ] == [
        (None, "Kent Pat", 5),
        (None, "Anton Malkov", 1),
    ]


def test_facebook_personal_chat_separates_name_only_senders(db_session):
    db_session.execute(
        text(
            "INSERT INTO account (id, platform, name, platform_user_id) "
            "VALUES (1, 'facebook', 'Anton Malkov', 'owner-123')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO chats "
            "(id, account_id, platform, chat_id, title, chat_type) "
            "VALUES (10, 1, 'facebook', 'friend_456', 'Friend', 'personal_chat')"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, platform, message_id, sender_id, sender_name, "
            "message_type, text_content, raw_payload) "
            "VALUES (:id, 10, 'facebook', :message_id, :sender_id, :sender_name, "
            "'message', 'synthetic text', '{}')"
        ),
        [
            {
                "id": index,
                "message_id": str(index),
                "sender_id": "owner-123",
                "sender_name": "Anton Malkov" if index == 1 else "Synthetic Friend",
            }
            for index in range(1, 4)
        ],
    )

    result = get_chat_insights(db_session, chat_id=10)

    assert [
        (sender.sender_id, sender.display_name, sender.message_count)
        for sender in result.chats[0].senders
    ] == [
        (None, "Synthetic Friend", 2),
        (None, "Anton Malkov", 1),
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
            "important thing важный нечто message MESSAGE"
        ),
    )

    result = ChatInsightsResponse(
        chats=[
            chat
            for chat_id in (10, 11, 12)
            for chat in get_chat_insights(db_session, chat_id=chat_id).chats
        ]
    )
    chat = result.chats[0]
    sender = chat.senders[0]

    excluded_words = {
        "не", "и", "я", "в", "а", "что", "это", "на", "ты", "с",
        "the", "and", "is", "not", "for", "on", "by", "we",
        "message",
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
        "important thing важный нечто message MESSAGE"
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

    result = ChatInsightsResponse(
        chats=[
            chat
            for chat_id in (10, 11, 12)
            for chat in get_chat_insights(db_session, chat_id=chat_id).chats
        ]
    )

    assert [chat.title for chat in result.chats] == ["Direct", "Group", "Supergroup"]
    direct = result.chats[0]
    assert direct.ordinary_message_count == 2
    assert direct.text_length == len("Hello hello ❤️ 👩‍💻hello world")
    assert direct.popular_words[0].word == "hello"
    assert direct.popular_words[0].count == 3
    assert direct.popular_emojis[0].emoji == "❤️"
    assert {sender.sender_id: sender.message_count for sender in direct.senders} == {
        "user100": 2
    }
    assert direct.reaction_count == 5
    assert [(item.emoji, item.count) for item in direct.reaction_emojis] == [
        ("💔", 4),
        ("👍", 1),
    ]
    assert direct.reactors[0].reactor_id == "user200"
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

    result = ChatInsightsResponse(
        chats=[
            chat
            for chat_id in (9, 10)
            for chat in get_chat_insights(db_session, chat_id=chat_id).chats
        ]
    )

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
        message_date=start + timedelta(minutes=15),
        text_content="Another reply",
        reply_to_telegram_message_id="2",
    )
    add_message(
        db_session,
        4,
        10,
        "message",
        "user200",
        message_date=start + timedelta(hours=12, minutes=20),
        raw_payload={"media_type": "voice_message", "duration_seconds": 8},
    )
    add_message(
        db_session,
        5,
        10,
        "message",
        "user-owner",
        message_date=start + timedelta(hours=12, minutes=25),
        raw_payload={"sticker_emoji": "🙂"},
        reply_to_telegram_message_id="missing",
    )
    add_message(
        db_session,
        6,
        10,
        "service",
        "user200",
        message_date=start + timedelta(hours=12, minutes=26),
        raw_payload={"action": "join_group"},
    )

    result = ChatInsightsResponse.model_validate(get_chat_insights(db_session))
    chat = result.chats[0]

    assert chat.reply_tempo.reply_reference_count == 3
    assert chat.reply_tempo.measured_reply_count == 2
    assert chat.reply_tempo.average_response_seconds == 450
    assert chat.reply_tempo.longest_response_seconds == 600
    assert chat.reply_tempo.median_response_seconds == 450
    assert chat.conversation_activity.session_gap_hours == 12
    assert chat.conversation_activity.session_count == 2
    assert chat.conversation_activity.sender_transition_count == 3
    assert chat.conversation_activity.sender_switch_count == 3
    assert chat.conversation_activity.sender_switch_percentage == 100
    assert chat.conversation_activity.longest_turn_taking_streak == 3
    assert {
        (sender.sender_id, sender.count)
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
    assert [(sender.display_name, sender.count) for sender in photo.senders] == [
        ("user-owner", 1)
    ]
    assert next(
        item for item in chat.message_type_breakdown if item.category == "Service event"
    ).senders[0].display_name == "user200"
    assert next(
        item for item in chat.message_type_breakdown if item.category == "Text"
    ).senders == []


def test_message_type_breakdown_ranks_five_senders_and_omits_plain_text_senders(
    db_session,
):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")

    message_id = 1
    for sender_number, message_count in enumerate(range(6, 0, -1), start=1):
        for _ in range(message_count):
            add_message(
                db_session,
                message_id,
                10,
                "message",
                f"user{sender_number}",
                raw_payload={"media_type": "photo"},
            )
            message_id += 1
    add_message(
        db_session,
        message_id,
        10,
        "message",
        "user-owner",
        text_content="plain text",
    )

    chat = ChatInsightsResponse.model_validate(get_chat_insights(db_session)).chats[0]
    photo = next(item for item in chat.message_type_breakdown if item.category == "Photo")
    text = next(item for item in chat.message_type_breakdown if item.category == "Text")

    assert [(sender.sender_id, sender.count) for sender in photo.senders] == [
        ("user1", 6),
        ("user2", 5),
        ("user3", 4),
        ("user4", 3),
        ("user5", 2),
    ]
    assert text.senders == []


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
    assert activity.opening_senders[0].sender_id is None
    assert activity.opening_senders[0].display_name == "Unknown sender"


def test_chat_insights_include_average_activity_times_and_calendar_patterns(db_session):
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
            db_session,
            message_id,
            10,
            "message",
            sender_id,
            message_date=message_date,
        )
    add_message(
        db_session,
        5,
        10,
        "service",
        "user-a",
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
        ("Monday", 1),
        ("Tuesday", 1),
        ("Wednesday", 1),
        ("Thursday", 1),
        ("Friday", 0),
        ("Saturday", 0),
        ("Sunday", 0),
    ]
    assert [(item.period, item.count) for item in chat.month_activity] == [
        ("January", 2),
        ("February", 2),
        ("March", 0),
        ("April", 0),
        ("May", 0),
        ("June", 0),
        ("July", 0),
        ("August", 0),
        ("September", 0),
        ("October", 0),
        ("November", 0),
        ("December", 0),
    ]


def test_average_activity_time_uses_circular_mean_around_midnight(db_session):
    add_account(db_session, 1, "user-owner")
    add_chat(db_session, 10, 1, "chat-10", "Direct", chat_type="personal_chat")
    add_message(
        db_session,
        1,
        10,
        "message",
        "user-a",
        message_date=datetime(2025, 1, 1, 23, 59, tzinfo=timezone.utc),
    )
    add_message(
        db_session,
        2,
        10,
        "message",
        "user-a",
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
