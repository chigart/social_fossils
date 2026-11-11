from zipfile import ZipFile

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app import vk_importer
from app.models import Account, Chat, Contact, ImportSession, Message
from app.telegram_importer import import_source_export


def _create_import_tables(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE account (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "platform VARCHAR(50), name VARCHAR(200), username VARCHAR(100), "
                "platform_user_id VARCHAR(100), created_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE canonical_identities ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, platform VARCHAR(50), "
                "platform_user_id VARCHAR(100), identity_group_id INTEGER, "
                "created_at DATETIME, UNIQUE(platform, platform_user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "account_id INTEGER, platform VARCHAR(50), platform_user_id VARCHAR(100), "
                "source_contact_key VARCHAR(64), canonical_identity_id INTEGER, "
                "display_name VARCHAR(300), username VARCHAR(100), created_at DATETIME, "
                "UNIQUE(account_id, platform_user_id), "
                "UNIQUE(account_id, source_contact_key))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE chats (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "account_id INTEGER, platform VARCHAR(50), chat_id VARCHAR(500), "
                "chat_type VARCHAR(50), title VARCHAR(300), created_at DATETIME, "
                "UNIQUE(account_id, chat_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "chat_id INTEGER, platform VARCHAR(50), message_id VARCHAR(100), "
                "source_record_key VARCHAR(64), sender_id VARCHAR(100), "
                "sender_contact_id INTEGER, sender_name VARCHAR(300), "
                "is_outgoing BOOLEAN, message_date DATETIME, message_type VARCHAR(50), "
                "text_content TEXT, reply_to_telegram_message_id VARCHAR(100), "
                "source_reply_id VARCHAR(200), raw_payload JSON, created_at DATETIME, "
                "UNIQUE(chat_id, message_id), "
                "UNIQUE(chat_id, source_record_key))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE import_sessions ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, "
                "platform VARCHAR(50), source_filename VARCHAR(500), "
                "file_sha256 VARCHAR(64), status VARCHAR(20), started_at DATETIME, "
                "finished_at DATETIME, total_messages INTEGER, inserted_messages INTEGER, "
                "updated_messages INTEGER, skipped_messages INTEGER, error_message TEXT, "
                "created_at DATETIME)"
            )
        )


def _write_archive(path):
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "profile/page-info.html",
            """<meta charset="utf-8">
            <div class="item">
              <div class="item__tertiary">Full name</div>
              <div>Антон Мальков</div>
            </div>""",
        )
        archive.writestr(
            "messages/123/messages0.html",
            """<div class="page_block_header_inner">
              <div class="ui_crumb">Sample Friend</div>
            </div>
            <div class="message" data-id="message-1">
              <div class="message__header">
                <a href="https://vk.com/id123">Sample Friend</a>
                5 мая 2024 в 12:30
              </div>
              <div>incoming text</div>
            </div>
            <div class="message" data-id="message-2">
              <div class="message__header">
                Вы 6 мая 2024 в 13:15
              </div>
              <div>outgoing text</div>
            </div>""",
        )


def _write_profileless_archive(path, message_text):
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "messages/123/messages0.html",
            f"""<div class="message" data-id="message-1">
              <div class="message__header">Unknown sender</div>
              <div>{message_text}</div>
            </div>""",
        )


def test_vk_import_is_idempotent_and_records_import_session(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'vk.db'}")
    _create_import_tables(engine)
    archive_path = tmp_path / "vk.zip"
    _write_archive(archive_path)

    with Session(engine) as session:
        first = vk_importer.import_vk_export(archive_path, session=session)

        assert first["platform"] == "vk"
        assert "account_name" not in first
        assert first["total_messages"] == 2
        assert first["inserted_messages"] == 2
        assert first["skipped_messages"] == 0
        account = session.scalar(select(Account))
        chat = session.scalar(select(Chat))
        assert account is not None
        assert account.platform == "vk"
        assert account.name == "Антон Мальков"
        assert account.username is None
        assert account.platform_user_id is not None
        assert account.platform_user_id.startswith("archive:")
        assert chat is not None
        assert chat.title == "Sample Friend"
        messages = session.scalars(
            select(Message).order_by(Message.message_date)
        ).all()
        assert [message.is_outgoing for message in messages] == [False, True]
        assert messages[0].sender_contact_id is not None
        assert messages[1].sender_contact_id is not None
        assert messages[1].sender_id == account.platform_user_id
        assert messages[1].is_outgoing is True
        assert messages[1].sender_name == "Антон Мальков"
        assert all(message.source_record_key for message in messages)

        messages[1].sender_name = "Вы"
        account.username = None
        session.flush()

        second = import_source_export("vk", archive_path, session=session)
        assert second["inserted_messages"] == 0
        assert second["skipped_messages"] == 2
        assert account.username is None
        assert messages[1].sender_name == "Антон Мальков"

        assert len(session.scalars(select(Contact)).all()) == 2
        sessions = session.scalars(
            select(ImportSession).order_by(ImportSession.id)
        ).all()
        assert [item.platform for item in sessions] == ["vk", "vk"]
        assert [
            (
                item.status,
                item.total_messages,
                item.inserted_messages,
                item.skipped_messages,
            )
            for item in sessions
        ] == [("completed", 2, 2, 0), ("completed", 2, 0, 2)]

    engine.dispose()


def test_vk_import_keeps_profileless_archive_accounts_separate(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'vk-profileless.db'}")
    _create_import_tables(engine)
    first_path = tmp_path / "first-profileless.zip"
    second_path = tmp_path / "second-profileless.zip"
    _write_profileless_archive(first_path, "first synthetic message")
    _write_profileless_archive(second_path, "second synthetic message")

    with Session(engine) as session:
        first = vk_importer.import_vk_export(first_path, session=session)
        second = vk_importer.import_vk_export(second_path, session=session)

        assert first["account_id"] != second["account_id"]
        accounts = session.scalars(select(Account)).all()
        chats = session.scalars(select(Chat)).all()
        assert len(accounts) == 2
        assert len({account.platform_user_id for account in accounts}) == 2
        assert len(chats) == 2
        assert len({chat.account_id for chat in chats}) == 2

    engine.dispose()


def test_vk_import_rolls_back_after_database_failure(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'vk-rollback.db'}")
    _create_import_tables(engine)
    archive_path = tmp_path / "vk.zip"
    _write_archive(archive_path)

    def fail_insert(*_args):
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(vk_importer, "_insert_message_batch", fail_insert)
    with Session(engine) as session:
        try:
            vk_importer.import_vk_export(archive_path, session=session)
        except RuntimeError as exc:
            assert str(exc) == "synthetic database failure"
        else:
            raise AssertionError("expected the import to fail")

        assert session.scalar(select(Account)) is None
        assert session.scalar(select(ImportSession)) is None
        assert session.scalar(select(Chat)) is None

    engine.dispose()
