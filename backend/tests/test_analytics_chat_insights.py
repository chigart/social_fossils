from app.routers.analytics_chat_insights import extract_emojis, get_chat_insights
from app.schemas.analytics import ChatInsightsResponse
from analytics_test_helpers import add_account, add_chat, add_message
from app.main import app


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
