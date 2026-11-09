import json
from zipfile import ZipFile

import pytest

from app.facebook_parser import parse_facebook_archive


def _write_conversation(archive, path, messages, **metadata):
    archive.writestr(path, json.dumps({"messages": messages, **metadata}))


def test_parse_facebook_archive_reads_profile_and_normalizes_messages(tmp_path):
    archive_path = tmp_path / "facebook.zip"
    thread_root = "your_facebook_activity/messages/inbox/friend_123"
    duplicate = {
        "sender_name": "Example Friend",
        "timestamp_ms": 1_700_000_000_123,
        "content": "synthetic message",
    }
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "your_facebook_activity/profile_information/profile_information.json",
            json.dumps(
                {
                    "profile_v2": {
                        "name": {"full_name": "Synthetic Owner"},
                        "username": {"value": "owner_handle"},
                        "user_id": {"value": "owner-123"},
                    }
                }
            ),
        )
        _write_conversation(
            archive,
            f"{thread_root}/message_1.json",
            [
                {
                    "sender_name": "Synthetic Owner",
                    "timestamp_ms": 1_700_000_000_000,
                    "content": "hello",
                    "type": "Generic",
                },
                duplicate,
                duplicate,
            ],
            title="Example conversation",
            participants=[
                {"name": "Synthetic Owner", "user_id": "owner-123"},
                {"name": "Example Friend", "user_id": "123"},
            ],
        )
        _write_conversation(
            archive,
            "your_facebook_activity/messages/inbox/deleted_user_999/message_1.json",
            [{"sender_name": "Deleted User", "content": "not imported"}],
        )

    parsed = parse_facebook_archive(archive_path)
    repeated = parse_facebook_archive(archive_path)

    assert parsed.account_name == "Synthetic Owner"
    assert parsed.account_username == "owner_handle"
    assert parsed.owner_platform_user_id == "owner-123"
    assert len(parsed.chats) == 1
    chat = parsed.chats[0]
    assert chat.platform_chat_id == "inbox/friend_123"
    assert chat.title == "Example conversation"
    assert chat.chat_type == "personal_chat"
    assert chat.correspondent_platform_user_id == "123"
    assert chat.correspondent_name == "Example Friend"
    assert [message["message_id"] for message in chat.messages] == [
        f"facebook:{message['source_record_key']}" for message in chat.messages
    ]
    assert chat.messages[0]["message_type"] == "message"
    assert chat.messages[0]["text_content"] == "hello"
    assert chat.messages[0]["message_date"].isoformat() == "2023-11-14T22:13:20+00:00"
    assert chat.messages[1]["source_record_key"] != chat.messages[2]["source_record_key"]
    assert [message["source_record_key"] for message in chat.messages] == [
        message["source_record_key"] for message in repeated.chats[0].messages
    ]
    assert [message["message_id"] for message in chat.messages] == [
        message["message_id"] for message in repeated.chats[0].messages
    ]


def test_facebook_uses_numeric_thread_folder_id_for_personal_chat(tmp_path):
    archive_path = tmp_path / "facebook-short-id.zip"
    long_user_id = "name:" + "a" * 64
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "profile_information/profile_information.json",
            json.dumps(
                {
                    "profile_v2": {
                        "name": {"full_name": "Synthetic Owner"},
                        "user_id": {"value": "owner-123"},
                    }
                }
            ),
        )
        _write_conversation(
            archive,
            "messages/inbox/friend_858127978920780/message_1.json",
            [
                {
                    "sender_name": "Synthetic Friend",
                    "sender_id": long_user_id,
                    "content": "synthetic incoming",
                }
            ],
            title="Synthetic conversation",
            participants=[
                {"name": "Synthetic Owner", "user_id": "owner-123"},
                {"name": "Synthetic Friend", "user_id": long_user_id},
            ],
        )
        _write_conversation(
            archive,
            "messages/inbox/friend_858127978920780/message_2.json",
            [
                {
                    "sender_name": "Synthetic Friend",
                    "sender_id": long_user_id,
                    "content": "synthetic incoming continuation",
                }
            ],
        )

    parsed = parse_facebook_archive(archive_path)

    chat = parsed.chats[0]
    assert chat.platform_chat_id == "inbox/friend_858127978920780"
    assert chat.correspondent_platform_user_id == "858127978920780"
    assert [message["sender_id"] for message in chat.messages] == [
        "858127978920780",
        "858127978920780",
    ]


def test_parse_facebook_archive_numbers_split_files_in_order(tmp_path):
    archive_path = tmp_path / "facebook-split.zip"
    with ZipFile(archive_path, "w") as archive:
        _write_conversation(
            archive,
            "messages/inbox/friend_123/message_2.json",
            [{"content": "third"}],
            title="Friend conversation",
        )
        _write_conversation(
            archive,
            "messages/inbox/friend_123/message_1.json",
            [{"content": "first"}, {"content": "second"}],
            title="Friend conversation",
        )

    parsed = parse_facebook_archive(archive_path)

    assert [
        message["text_content"] for message in parsed.chats[0].messages
    ] == ["first", "second", "third"]


def test_parse_facebook_archive_skips_untitled_conversations(tmp_path):
    archive_path = tmp_path / "facebook-untitled.zip"
    with ZipFile(archive_path, "w") as archive:
        _write_conversation(
            archive,
            "messages/inbox/deleted_user_123/message_1.json",
            [{"content": "deleted account message"}],
            participants=[{"name": "Owner"}, {"name": "Deleted User"}],
        )

    parsed = parse_facebook_archive(archive_path)

    assert parsed.chats == []


def test_parse_facebook_archive_repairs_thai_and_georgian_text(tmp_path):
    archive_path = tmp_path / "facebook-mojibake.zip"
    thai_name = "ลิขิต · Dumbbell Kit 20kg"
    georgian_name = "დღიურად ბინა სოლოლაკში"
    georgian_clinic = 'ჯავრიშვილის კლინიკა "ოფთალმიჯი" Javrishvili Eye Clinic "Oftalmij"'
    cyrillic_name = "Тестовый Собеседник"
    mojibake_thai = thai_name.encode("utf-8").decode("latin-1")
    mojibake_georgian = georgian_name.encode("utf-8").decode("latin-1")
    mojibake_clinic = georgian_clinic.encode("utf-8").decode("latin-1")
    mojibake_russian = cyrillic_name.encode("utf-8").decode("latin-1")
    truncated_mojibake_russian = mojibake_russian[:-1]

    with ZipFile(archive_path, "w") as archive:
        _write_conversation(
            archive,
            "messages/inbox/georgian_123/message_1.json",
            [
                {
                    "sender_name": mojibake_georgian,
                    "content": mojibake_thai,
                },
                {
                    "sender_name": mojibake_russian,
                    "content": mojibake_russian,
                },
                {
                    "sender_name": truncated_mojibake_russian,
                    "content": truncated_mojibake_russian,
                },
                {"content": "Olá"},
            ],
            title=mojibake_clinic,
        )

    parsed = parse_facebook_archive(archive_path)

    chat = parsed.chats[0]
    assert chat.title == georgian_clinic
    assert chat.messages[0]["sender_name"] == georgian_name
    assert chat.messages[0]["text_content"] == thai_name
    assert chat.messages[1]["sender_name"] == cyrillic_name
    assert chat.messages[1]["text_content"] == cyrillic_name
    expected_truncated_name = cyrillic_name.encode("utf-8")[:-1].decode(
        "utf-8",
        errors="replace",
    )
    assert chat.messages[2]["sender_name"] == expected_truncated_name
    assert chat.messages[2]["text_content"] == expected_truncated_name
    assert chat.messages[3]["text_content"] == "Olá"


def test_parse_facebook_archive_preserves_cyrillic_name_ending_in_u0085(tmp_path):
    archive_path = tmp_path / "facebook-cyrillic-name.zip"
    expected_name = "Анастасия Липецких"
    mojibake_name = expected_name.encode("utf-8").decode("latin-1")

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "profile_information/profile_information.json",
            json.dumps(
                {
                    "profile_v2": {
                        "name": {"full_name": mojibake_name},
                        "username": {"value": "owner_handle"},
                        "user_id": {"value": "owner-123"},
                    }
                }
            ),
        )
        _write_conversation(
            archive,
            "messages/inbox/friend_123/message_1.json",
            [
                {
                    "sender_name": mojibake_name,
                    "content": mojibake_name,
                }
            ],
            title=mojibake_name,
            participants=[
                {"name": "Profile Owner", "user_id": "owner-123"},
                {"name": "Synthetic Friend", "user_id": "friend-123"},
            ],
        )

    parsed = parse_facebook_archive(archive_path)

    chat = parsed.chats[0]
    assert parsed.account_name == expected_name
    assert chat.title == expected_name
    assert chat.messages[0]["sender_name"] == expected_name
    assert chat.messages[0]["text_content"] == expected_name


def test_parse_facebook_archive_rejects_invalid_and_malformed_archives(tmp_path):
    invalid_path = tmp_path / "invalid.zip"
    invalid_path.write_text("not a zip archive", encoding="utf-8")
    with pytest.raises(ValueError, match="valid ZIP"):
        parse_facebook_archive(invalid_path)

    unsupported_path = tmp_path / "unsupported.zip"
    with ZipFile(unsupported_path, "w") as archive:
        archive.writestr("unrelated.json", "{}")
    with pytest.raises(ValueError, match="no supported message"):
        parse_facebook_archive(unsupported_path)

    malformed_path = tmp_path / "malformed.zip"
    with ZipFile(malformed_path, "w") as archive:
        archive.writestr(
            "messages/inbox/friend_123/message_1.json",
            json.dumps({"messages": ["not an object"]}),
        )
    with pytest.raises(ValueError, match="entries must be JSON objects"):
        parse_facebook_archive(malformed_path)


def test_profileless_archives_have_distinct_stable_owner_ids(tmp_path):
    first_path = tmp_path / "first.zip"
    second_path = tmp_path / "second.zip"
    for path, content in ((first_path, "first export"), (second_path, "second export")):
        with ZipFile(path, "w") as archive:
            _write_conversation(
                archive,
                "messages/inbox/friend_123/message_1.json",
                [{"content": content}],
                title="Synthetic conversation",
            )

    first = parse_facebook_archive(first_path)
    repeated_first = parse_facebook_archive(first_path)
    second = parse_facebook_archive(second_path)

    assert first.has_owner_identity is False
    assert first.owner_platform_user_id == repeated_first.owner_platform_user_id
    assert first.owner_platform_user_id != second.owner_platform_user_id


def test_parse_facebook_archive_rejects_message_data_over_memory_limit(
    tmp_path,
    monkeypatch,
):
    archive_path = tmp_path / "oversized-messages.zip"
    with ZipFile(archive_path, "w") as archive:
        _write_conversation(
            archive,
            "messages/inbox/friend_123/message_1.json",
            [{"content": "synthetic"}],
            title="Synthetic conversation",
        )

    monkeypatch.setattr("app.facebook_parser.MAX_MESSAGE_DATA_BYTES", 1)

    with pytest.raises(ValueError, match="message data exceeds"):
        parse_facebook_archive(archive_path)


def test_parse_facebook_archive_rejects_oversized_message_file(tmp_path, monkeypatch):
    archive_path = tmp_path / "oversized-message-file.zip"
    with ZipFile(archive_path, "w") as archive:
        _write_conversation(
            archive,
            "messages/inbox/friend_123/message_1.json",
            [{"content": "synthetic"}],
            title="Synthetic conversation",
        )

    monkeypatch.setattr("app.facebook_parser.MAX_MESSAGE_FILE_BYTES", 1)

    with pytest.raises(ValueError, match="message JSON file exceeds"):
        parse_facebook_archive(archive_path)
