import json
import logging
from types import SimpleNamespace

from app import importer


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def add(self, _instance):
        pass

    def flush(self):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_import_logs_progress_without_chat_titles_or_message_text(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=importer.__name__)
    private_text = "private message text"
    parsed_chat = SimpleNamespace(
        title="private chat title",
        messages=[{"text_content": private_text}],
    )
    parsed_export = SimpleNamespace(
        owner_telegram_id="user123",
        account_name="Example",
        chats=[parsed_chat],
    )
    account = SimpleNamespace(id=1, name="Example", telegram_user_id="user123")
    session = FakeSession()

    monkeypatch.setattr(importer, "parse_telegram_export", lambda _payload: parsed_export)
    monkeypatch.setattr(importer, "get_or_create_account", lambda *_args: account)
    monkeypatch.setattr(importer, "ensure_chat", lambda *_args: SimpleNamespace(id=1))
    monkeypatch.setattr(importer, "insert_message", lambda *_args: True)

    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps({"synthetic": True}), encoding="utf-8")

    importer.import_telegram_export(export_path, session=session)

    messages = [record.getMessage() for record in caplog.records]
    assert any("Parsed Telegram export: 1 chats, 1 messages" in message for message in messages)
    assert any("Processing chat 1/1 (1 messages)" in message for message in messages)
    assert any("Import completed: 1 messages processed, 1 inserted, 0 skipped" in message for message in messages)
    assert all(private_text not in message for message in messages)
    assert all(parsed_chat.title not in message for message in messages)
    assert session.committed
    assert not session.rolled_back
