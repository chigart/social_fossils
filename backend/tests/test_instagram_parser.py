import json
from zipfile import ZipFile

import pytest

from app.instagram_parser import parse_instagram_archive


def _write_conversation(archive: ZipFile, path: str, messages, **metadata) -> None:
    archive.writestr(
        path,
        json.dumps({"messages": messages, **metadata}),
    )


def test_parse_instagram_archive_preserves_messages_and_generates_stable_keys(tmp_path):
    archive_path = tmp_path / "instagram.zip"
    thread_root = "your_instagram_activity/messages/inbox/friend_123"
    repeated_message = {
        "sender_name": "Example Friend",
        "timestamp_ms": 1_700_000_000_123,
        "content": "synthetic message",
    }
    with ZipFile(archive_path, "w") as archive:
        _write_conversation(
            archive,
            f"{thread_root}/message_1.json",
            [
                {
                    "message_id": "source-1",
                    "sender_id": "user-1",
                    "sender_name": "Owner",
                    "timestamp_ms": 1_700_000_000_000,
                    "content": "hello",
                    "is_outgoing": True,
                },
                repeated_message,
                repeated_message,
            ],
            title="Example conversation",
            participants=[{"name": "Owner"}, {"name": "Friend"}, {"name": "Other"}],
        )

    parsed = parse_instagram_archive(str(archive_path))
    repeated = parse_instagram_archive(str(archive_path))

    assert parsed.account_name == "Instagram account"
    assert parsed.owner_platform_user_id is None
    assert len(parsed.chats) == 1
    chat = parsed.chats[0]
    assert chat.platform_chat_id == "123"
    assert chat.legacy_platform_chat_id == "inbox/friend_123"
    assert chat.correspondent_platform_user_id == "123"
    assert chat.correspondent_username == "friend"
    assert chat.title == "Example conversation"
    assert chat.chat_type == "private_group"
    assert len(chat.messages) == 3

    first, second, third = chat.messages
    assert first["source_message_id"] == "source-1"
    assert first["sender_platform_user_id"] == "user-1"
    assert first["is_outgoing"] is True
    assert first["text_content"] == "hello"
    assert first["raw_payload"]["content"] == "hello"
    assert first["message_date"].isoformat() == "2023-11-14T22:13:20+00:00"
    assert second["is_outgoing"] is None
    assert second["source_message_id"] is None
    assert second["source_record_key"] != third["source_record_key"]
    assert [
        message["source_record_key"] for message in chat.messages
    ] == [
        message["source_record_key"] for message in repeated.chats[0].messages
    ]


def test_parse_instagram_archive_rejects_invalid_or_unsupported_archives(tmp_path):
    invalid_path = tmp_path / "invalid.zip"
    invalid_path.write_text("not a zip archive", encoding="utf-8")
    with pytest.raises(ValueError, match="valid ZIP"):
        parse_instagram_archive(str(invalid_path))

    unsupported_path = tmp_path / "unsupported.zip"
    with ZipFile(unsupported_path, "w") as archive:
        archive.writestr("unrelated.json", "{}")
    with pytest.raises(ValueError, match="no supported message"):
        parse_instagram_archive(str(unsupported_path))


def test_parse_instagram_archive_reads_account_identity_from_profile_data(tmp_path):
    archive_path = tmp_path / "profile.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "personal_information/personal_information.json",
            json.dumps(
                {
                    "profile_user": [
                        {
                            "string_map_data": {
                                "Username": {"value": "owner_handle"},
                                "Name": {"value": "Owner Display Name"},
                                "User ID": {"value": "user-123"},
                            }
                        }
                    ]
                }
            ),
        )
        _write_conversation(
            archive,
            "messages/inbox/thread_123/message_1.json",
            [],
        )

    parsed = parse_instagram_archive(archive_path)

    assert parsed.account_name == "Owner Display Name"
    assert parsed.account_username == "owner_handle"
    assert parsed.owner_platform_user_id == "user-123"


def test_parse_instagram_archive_repairs_latin1_mojibake(tmp_path):
    archive_path = tmp_path / "mojibake.zip"
    mojibake_name = "Ð\u0098Ð²Ð°Ð½ Ð§Ð¾Ð¿Ð¾Ð±ÐµÑ\u0081Ð¾Ð²"
    with ZipFile(archive_path, "w") as archive:
        _write_conversation(
            archive,
            "messages/inbox/person_123/message_1.json",
            [
                {
                    "sender_name": mojibake_name,
                    "content": mojibake_name,
                }
            ],
            title=mojibake_name,
        )

    parsed = parse_instagram_archive(archive_path)

    assert parsed.chats[0].title == "Иван Чопобесов"
    assert parsed.chats[0].messages[0]["sender_name"] == "Иван Чопобесов"
    assert parsed.chats[0].messages[0]["text_content"] == "Иван Чопобесов"


def test_parse_instagram_archive_rejects_malformed_conversation_entries(tmp_path):
    archive_path = tmp_path / "malformed.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "messages/inbox/thread/message_1.json",
            json.dumps({"messages": ["not an object"]}),
        )

    with pytest.raises(ValueError, match="entries must be JSON objects"):
        parse_instagram_archive(str(archive_path))
