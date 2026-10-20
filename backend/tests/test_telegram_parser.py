from datetime import datetime, timezone

import pytest

from app.telegram_parser import (
    determine_is_outgoing,
    extract_account_name,
    extract_sender_id,
    extract_sender_name,
    flatten_message_text,
    normalize_user_id,
    parse_datetime,
    parse_message_record,
    parse_message_timestamp,
    parse_telegram_export,
)


def test_normalize_user_id_handles_numeric_and_prefixed_ids():
    assert normalize_user_id(8518403760) == "user8518403760"
    assert normalize_user_id("8518403760") == "user8518403760"
    assert normalize_user_id("user8518403760") == "user8518403760"
    assert normalize_user_id("-5") is None
    assert normalize_user_id(None) is None
    assert normalize_user_id("abc") is None


def test_flatten_message_text_supports_string_and_entity_lists():
    assert flatten_message_text("hello") == "hello"
    assert flatten_message_text(["hello", {"text": " world"}]) == "hello world"
    assert flatten_message_text({"text": "Test"}) == "Test"
    assert flatten_message_text({"foo": "bar"}) is None
    assert flatten_message_text(None) is None


def test_parse_datetime_accepts_unix_and_iso_values_and_rejects_invalid_input():
    assert parse_datetime(1776779645) == datetime.fromtimestamp(1776779645, tz=timezone.utc)
    assert parse_datetime("2026-04-21T16:54:05+00:00") == datetime(2026, 4, 21, 16, 54, 5, tzinfo=timezone.utc)
    assert parse_datetime("2026-04-21T16:54:05") is None
    assert parse_datetime("not-a-date") is None
    assert parse_datetime(None) is None


def test_parse_message_timestamp_prefers_unix_before_iso():
    message = {"date_unixtime": "1776779645", "date": "2026-04-21T16:54:05+00:00"}
    assert parse_message_timestamp(message) == datetime.fromtimestamp(1776779645, tz=timezone.utc)

    message_without_unix = {"date": "2026-04-21T16:54:05+00:00"}
    assert parse_message_timestamp(message_without_unix) == datetime(2026, 4, 21, 16, 54, 5, tzinfo=timezone.utc)


def test_extract_account_name_and_sender_helpers():
    personal = {"first_name": "Alice", "last_name": "Smith"}
    assert extract_account_name(personal) == "Alice Smith"
    assert extract_account_name({}) == "Telegram account"

    message = {"from_id": "8518403760", "from": "Alice", "actor_id": "user123", "actor": "Bot"}
    assert extract_sender_id(message) == "user8518403760"
    assert extract_sender_name(message) == "Alice"

    assert determine_is_outgoing("user8518403760", "user8518403760") is True
    assert determine_is_outgoing("user123", "user8518403760") is False
    assert determine_is_outgoing(None, "user8518403760") is None


def test_parse_message_record_handles_missing_ids_and_reply_reference():
    message = {
        "id": "250",
        "type": "message",
        "date_unixtime": "1776779645",
        "from_id": "user8518403760",
        "from": "Alice",
        "text": ["hello", {"text": " world"}],
        "reply_to_message_id": 7,
    }
    parsed = parse_message_record(message, "user8518403760")

    assert parsed is not None
    assert parsed["telegram_message_id"] == "250"
    assert parsed["sender_telegram_id"] == "user8518403760"
    assert parsed["sender_name"] == "Alice"
    assert parsed["is_outgoing"] is True
    assert parsed["message_date"] == datetime.fromtimestamp(1776779645, tz=timezone.utc)
    assert parsed["text_content"] == "hello world"
    assert parsed["reply_to_telegram_message_id"] == "7"
    assert parsed["raw_payload"] == message

    assert parse_message_record({"type": "message", "date": "2026-04-21T16:54:05+00:00"}, "user10") is None
    assert parse_message_record({"id": "abc"}, "user10") is None


def test_parse_telegram_export_extracts_account_and_chat_messages():
    export = {
        "personal_information": {"user_id": 8518403760, "first_name": "Alice", "last_name": "Smith"},
        "contacts": {"list": [{"first_name": "Bob", "id": "user999"}, {"first_name": "skip"}]},
        "chats": {
            "list": [
                {
                    "name": "Example chat",
                    "type": "private_group",
                    "id": 5183596517,
                    "messages": [
                        {
                            "id": 250,
                            "type": "message",
                            "date": "2026-04-21T16:54:05",
                            "date_unixtime": "1776779645",
                            "from": "Example User",
                            "from_id": "user8518403760",
                            "text": "Example message",
                            "text_entities": [],
                        },
                        {
                            "id": 251,
                            "type": "service",
                            "date": "2026-04-21T16:55:05",
                            "date_unixtime": "1776779705",
                            "actor": "Bot",
                            "actor_id": "user12345",
                            "text": ["joined the group", {"text": "!"}],
                        },
                        {"id": None, "type": "skip"},
                    ],
                },
                {
                    "name": "Феодор",
                    "type": "personal_chat",
                    "id": 827793749,
                    "messages": [
                        {
                            "id": 251,
                            "from": "Alice Smith",
                            "from_id": "user8518403760",
                        },
                        {
                            "id": 252,
                            "from": "Феодор",
                            "from_id": "user827793749",
                        },
                        {
                            "id": 253,
                            "from": "Феодор Иванов",
                            "from_id": "user827793749",
                        },
                    ],
                },
                {
                    "name": "Alice",
                    "first_name": "Alice",
                    "last_name": "Jones",
                    "type": "personal_chat",
                    "id": 827793750,
                    "messages": [],
                },
                {"id": "bad", "messages": ["not-a-dict"]},
            ]
        },
    }

    parsed = parse_telegram_export(export)

    assert parsed.owner_telegram_id == "user8518403760"
    assert parsed.account_name == "Alice Smith"
    assert len(parsed.chats) == 4
    assert parsed.chats[0].telegram_chat_id == "5183596517"
    assert parsed.chats[0].title == "Example chat"
    assert parsed.chats[0].messages[0]["is_outgoing"] is True
    assert parsed.chats[0].messages[0]["message_date"] == datetime.fromtimestamp(1776779645, tz=timezone.utc)
    assert parsed.chats[0].messages[1]["message_type"] == "service"
    assert parsed.chats[0].messages[1]["text_content"] == "joined the group!"
    assert len(parsed.chats[0].messages) == 2
    assert parsed.chats[1].title == "Феодор"
    assert parsed.chats[2].title == "Alice"
    assert parsed.contacts == [{"first_name": "Bob", "id": "user999"}, {"first_name": "skip"}]
    assert parsed.raw == export


def test_parse_telegram_export_validates_top_level_types():
    with pytest.raises(ValueError, match="Telegram export payload must be a JSON object"):
        parse_telegram_export([])

    with pytest.raises(ValueError, match="personal_information must be an object"):
        parse_telegram_export({"personal_information": "bad"})

    with pytest.raises(ValueError, match="contacts must be an object when present"):
        parse_telegram_export({"personal_information": {}, "contacts": ["bad"], "chats": {}})

    with pytest.raises(ValueError, match="chats must be an object"):
        parse_telegram_export({"personal_information": {}, "contacts": {}, "chats": ["bad"]})
