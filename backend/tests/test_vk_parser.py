from zipfile import ZipFile

import pytest

from app.vk_parser import parse_vk_archive


def _write_archive(path, *, include_profile=True):
    with ZipFile(path, "w") as archive:
        if include_profile:
            profile = """<!doctype html>
                <meta charset="windows-1251">
                <div class="item">
                  <div class="item__tertiary">Полное имя</div>
                  <div>Sample VK Owner</div>
                </div>"""
            archive.writestr(
                "profile/page-info.html",
                profile.encode("windows-1251"),
            )
        archive.writestr(
            "messages/123/messages0.html",
            """<!doctype html><meta charset="utf-8">
            <div class="page_block_header_inner">
              <a class="ui_crumb">Messages</a>
              <div class="ui_crumb">Sample Friend</div>
            </div>
            <div class="item"><div class="item__main">
              <div class="message" data-id="message-1">
                <div class="message__header">
                  <a href="https://vk.com/id123">Sample Friend</a>
                  5 мая 2024 в 12:30
                </div>
                <div>incoming text<br>second line</div>
              </div>
            </div></div>
            <div class="item"><div class="item__main">
              <div class="message" data-id="message-2">
                <div class="message__header">
                  Sample VK Owner 6 мая 2024 в 13:15
                </div>
                <div>outgoing text</div>
              </div>
            </div></div>
            <div class="item"><div class="item__main">
              <div class="message" data-id="message-3">
                <div class="message__header">
                  <a href="https://vk.com/id123">Sample Friend</a>
                  7 мая 2024 в 14:45
                </div>
                <div></div>
                <div class="kludges">
                  <div class="attachment">
                    <div class="attachment__description">Photo</div>
                    <a class="attachment__link" href="https://example.test/media">
                      Original image
                    </a>
                  </div>
                </div>
              </div>
            </div></div>""",
        )
        archive.writestr(
            "messages/123/messages50.html",
            """<div class="item"><div class="item__main">
              <div class="message" data-id="message-4">
                <div class="message__header">
                  <a href="https://vk.com/id123">Sample Friend</a>
                  8 мая 2024 в 15:00
                </div>
                <div>last page message</div>
              </div>
              <div class="message" data-id="message-5">
                <div class="message__header">Вы 9 мая 2024 в 16:00</div>
                <div>owner page message</div>
              </div>
            </div></div>""",
        )


def test_parse_vk_archive_extracts_profile_conversation_and_messages(tmp_path):
    archive_path = tmp_path / "vk.zip"
    _write_archive(archive_path)

    parsed = parse_vk_archive(archive_path)

    assert parsed.account_name == "Sample VK Owner"
    assert parsed.account_username is None
    assert parsed.owner_platform_user_id is None
    assert len(parsed.chats) == 1
    chat = parsed.chats[0]
    assert chat.platform_chat_id == "123"
    assert chat.title == "Sample Friend"
    assert chat.chat_type == "personal_chat"
    assert chat.correspondent_platform_user_id == "123"
    assert chat.correspondent_name == "Sample Friend"
    assert [message["message_id"] for message in chat.messages] == [
        "message-1",
        "message-2",
        "message-3",
        "message-4",
        "message-5",
    ]
    assert chat.messages[0]["text_content"] == "incoming text\nsecond line"
    assert chat.messages[0]["sender_id"] == "123"
    assert chat.messages[0]["is_outgoing"] is False
    assert chat.messages[0]["message_date"].isoformat() == (
        "2024-05-05T12:30:00+00:00"
    )
    assert chat.messages[1]["sender_name"] == "Sample VK Owner"
    assert chat.messages[1]["is_outgoing"] is True
    assert chat.messages[4]["sender_name"] == "Вы"
    assert chat.messages[4]["is_outgoing"] is True
    assert chat.messages[2]["text_content"] is None
    assert chat.messages[2]["message_type"] == "attachment"
    assert chat.messages[2]["raw_payload"]["attachments"] == [
        {"description": "Photo", "label": "Original image"}
    ]
    assert "https://example.test/media" not in repr(chat.messages[2]["raw_payload"])


def test_parse_vk_archive_generates_stable_keys_for_messages_without_ids(tmp_path):
    archive_path = tmp_path / "vk-no-message-ids.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "messages/123/messages0.html",
            """<div class="message">
              <div class="message__header">Unknown sender</div>
              <div>same message</div>
            </div>
            <div class="message">
              <div class="message__header">Unknown sender</div>
              <div>same message</div>
            </div>""",
        )

    parsed = parse_vk_archive(archive_path)
    messages = parsed.chats[0].messages
    repeated = parse_vk_archive(archive_path).chats[0].messages

    assert len(messages) == 2
    assert messages[0]["message_id"] != messages[1]["message_id"]
    assert [
        message["source_record_key"] for message in messages
    ] == [
        message["source_record_key"] for message in repeated
    ]
    assert all(message["is_outgoing"] is None for message in messages)


def test_parse_vk_archive_rejects_invalid_and_unsupported_archives(tmp_path):
    invalid_path = tmp_path / "invalid.zip"
    invalid_path.write_text("not a ZIP archive", encoding="utf-8")
    with pytest.raises(ValueError, match="valid ZIP"):
        parse_vk_archive(invalid_path)

    unsupported_path = tmp_path / "unsupported.zip"
    with ZipFile(unsupported_path, "w") as archive:
        archive.writestr("profile/page-info.html", "<html></html>")
    with pytest.raises(ValueError, match="no supported message HTML"):
        parse_vk_archive(unsupported_path)

    no_messages_path = tmp_path / "empty-messages.zip"
    with ZipFile(no_messages_path, "w") as archive:
        archive.writestr(
            "messages/123/messages0.html",
            '<div class="item">no message container</div>',
        )
    with pytest.raises(ValueError, match="no supported messages"):
        parse_vk_archive(no_messages_path)
