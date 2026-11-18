from collections import Counter
from sqlalchemy import text

from app.constants import STOP_WORDS
from app.routers.analytics_chat_insights_content import _rank_words
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


def test_chat_insights_include_public_supergroups_in_picker_and_selected_results(
    db_session,
):
    add_account(db_session, 1, "user-owner")
    add_chat(
        db_session,
        733,
        1,
        "public-supergroup-733",
        "Public supergroup",
        chat_type="public_supergroup",
    )
    add_message(db_session, 1, 733, "message", "peer-733", text_content="hello")

    result = get_chat_insights(db_session, chat_id=733)

    assert [chat.chat_id for chat in result.chats] == [733]
    assert any(option.value == "733" for option in result.options)


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
