import json
from zipfile import ZipFile

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app import instagram_importer
from app.telegram_importer import import_source_export
from app.models import (
    CanonicalIdentity,
    Contact,
    ImportSession,
    Message,
    Account,
)


def _create_import_tables(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE account ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, platform VARCHAR(50) NOT NULL, "
                "name VARCHAR(200) NOT NULL, username VARCHAR(100), "
                "platform_user_id VARCHAR(100), "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE canonical_identities ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, platform VARCHAR(50), "
                "platform_user_id VARCHAR(100), created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(platform, platform_user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE contacts ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, "
                "platform VARCHAR(50), telegram_user_id VARCHAR(100), "
                "platform_user_id VARCHAR(100), canonical_identity_id INTEGER, "
                "display_name VARCHAR(300), username VARCHAR(100), "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(account_id, platform_user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE chats ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, "
                "platform VARCHAR(50), chat_id VARCHAR(500), chat_type VARCHAR(50), "
                "title VARCHAR(300), created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(account_id, chat_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, "
                "platform VARCHAR(50), message_id VARCHAR(100), "
                "source_message_id VARCHAR(200), source_record_key VARCHAR(64), "
                "sender_id VARCHAR(100), sender_platform_user_id VARCHAR(100), "
                "sender_contact_id INTEGER, sender_name VARCHAR(300), "
                "is_outgoing BOOLEAN, message_date DATETIME, message_type VARCHAR(50), "
                "text_content TEXT, reply_to_telegram_message_id VARCHAR(100), "
                "source_reply_id VARCHAR(200), raw_payload JSON, "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(chat_id, source_message_id), "
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
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
        )


def _write_archive(path) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "your_instagram_activity/personal_information/personal_information.json",
            json.dumps(
                {
                    "profile_user": [
                        {
                            "string_map_data": {
                                "Username": {"value": "synthetic_owner"},
                                "Name": {"value": "Synthetic Owner"},
                            }
                        }
                    ]
                }
            ),
        )
        archive.writestr(
            "your_instagram_activity/messages/inbox/example_123/message_1.json",
            json.dumps(
                {
                    "title": "Synthetic thread",
                    "participants": [{"name": "Owner"}, {"name": "Friend"}],
                    "messages": [
                        {
                            "sender_name": "Friend",
                            "timestamp_ms": 1_700_000_000_123,
                            "content": "synthetic private text",
                        },
                        {
                            "message_id": "instagram-message-2",
                            "sender_id": "instagram-user-2",
                            "sender_name": "Synthetic sender",
                            "timestamp_ms": 1_700_000_000_456,
                            "content": "synthetic identified message",
                        },
                    ],
                }
            ),
        )


def test_import_instagram_archive_is_idempotent_and_preserves_provenance(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'instagram.db'}")
    _create_import_tables(engine)
    archive_path = tmp_path / "instagram.zip"
    _write_archive(archive_path)

    with Session(engine) as session:
        first = instagram_importer.import_instagram_export(
            archive_path,
            session=session,
        )
        second = import_source_export(
            "instagram",
            archive_path,
            session=session,
        )

        assert first["platform"] == "instagram"
        assert first["inserted_messages"] == 2
        assert second["inserted_messages"] == 0
        assert second["skipped_messages"] == 2

        account = session.scalar(select(Account))
        messages = session.scalars(select(Message)).all()
        identified_message = session.scalar(
            select(Message).where(
                Message.source_message_id == "instagram-message-2"
            )
        )
        contact = session.scalar(select(Contact))
        identity = session.scalar(select(CanonicalIdentity))
        import_sessions = session.scalars(select(ImportSession)).all()
        assert account is not None
        assert account.platform == "instagram"
        assert account.platform_user_id == "synthetic_owner"
        assert account.username == "synthetic_owner"
        assert account.name == "Synthetic Owner"
        assert len(messages) == 2
        unidentified_message = next(
            message for message in messages if message.source_message_id is None
        )
        assert unidentified_message.platform == "instagram"
        assert unidentified_message.source_record_key
        assert unidentified_message.sender_id is None
        assert unidentified_message.sender_contact_id is None
        assert unidentified_message.is_outgoing is None
        assert unidentified_message.raw_payload["content"] == "synthetic private text"
        assert identified_message is not None
        assert contact is not None
        assert identified_message.sender_platform_user_id == "instagram-user-2"
        assert identified_message.sender_contact_id == contact.id
        assert contact.platform == "instagram"
        assert contact.telegram_user_id is None
        assert contact.platform_user_id == "instagram-user-2"
        assert identity is not None and identity.platform == "instagram"
        assert len(import_sessions) == 2
        assert all(item.platform == "instagram" for item in import_sessions)

    engine.dispose()


def test_instagram_import_rolls_back_on_database_failure(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'rollback.db'}")
    _create_import_tables(engine)
    archive_path = tmp_path / "instagram.zip"
    _write_archive(archive_path)

    def fail_insert(*_args):
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(instagram_importer, "_insert_message", fail_insert)
    with Session(engine) as session:
        try:
            instagram_importer.import_instagram_export(
                archive_path,
                session=session,
            )
        except RuntimeError as exc:
            assert str(exc) == "synthetic database failure"
        else:
            raise AssertionError("expected the import to fail")

        assert session.scalar(select(Account)) is None
        assert session.scalar(select(ImportSession)) is None

    engine.dispose()


def test_import_dispatch_rejects_unknown_platform():
    try:
        import_source_export("unsupported", "unused")
    except ValueError as exc:
        assert "Unsupported import platform" in str(exc)
    else:
        raise AssertionError("expected unsupported platform to fail")
