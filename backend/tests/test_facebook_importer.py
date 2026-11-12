import json
from zipfile import ZipFile

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app import facebook_importer
from app.models import (
    Account,
    Chat,
    Contact,
    ImportSession,
    Message,
)
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
                "UNIQUE(chat_id, message_id), UNIQUE(chat_id, source_record_key))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE import_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "account_id INTEGER, platform VARCHAR(50), source_filename VARCHAR(500), "
                "file_sha256 VARCHAR(64), status VARCHAR(20), started_at DATETIME, "
                "finished_at DATETIME, total_messages INTEGER, inserted_messages INTEGER, "
                "updated_messages INTEGER, skipped_messages INTEGER, error_message TEXT, "
                "created_at DATETIME)"
            )
        )


def _write_archive(
    path,
    *,
    include_profile=True,
    friend_name="Synthetic Friend",
    extra_messages=None,
):
    with ZipFile(path, "w") as archive:
        if include_profile:
            archive.writestr(
                "profile_information/profile_information.json",
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
        archive.writestr(
            "messages/inbox/friend_456/message_1.json",
            json.dumps(
                {
                    "title": "Synthetic conversation",
                    "participants": [
                        {"name": "Synthetic Owner", "user_id": "owner-123"},
                        {"name": friend_name, "user_id": "friend-456"},
                    ],
                    "messages": [
                        *(extra_messages or []),
                        {
                            "sender_name": "Synthetic Owner",
                            "sender_id": "owner-123",
                            "timestamp_ms": 1_700_000_000_000,
                            "content": "synthetic outgoing",
                        },
                        {
                            "sender_name": friend_name,
                            "sender_id": "friend-456",
                            "timestamp_ms": 1_700_000_000_001,
                            "content": "synthetic incoming",
                        },
                    ],
                }
            ),
        )


def test_facebook_import_is_idempotent_and_classifies_outgoing_messages(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'facebook.db'}")
    _create_import_tables(engine)
    archive_path = tmp_path / "facebook.zip"
    _write_archive(archive_path)

    with Session(engine) as session:
        first = facebook_importer.import_facebook_export(archive_path, session=session)
        second = import_source_export("facebook", archive_path, session=session)

        assert first["platform"] == "facebook"
        assert first["total_messages"] == 2
        assert first["inserted_messages"] == 2
        assert first["skipped_messages"] == 0
        assert second["inserted_messages"] == 0
        assert second["skipped_messages"] == 2
        account = session.scalar(select(Account))
        chat = session.scalar(select(Chat))
        assert account is not None and account.platform == "facebook"
        assert chat is not None and chat.title == "Synthetic conversation"
        messages = session.scalars(
            select(Message).order_by(Message.message_date)
        ).all()
        assert [message.is_outgoing for message in messages] == [True, False]
        assert all(message.source_record_key for message in messages)
        assert all(message.sender_contact_id is not None for message in messages)
        assert messages[1].sender_id == "456"
        friend_contact = session.scalar(
            select(Contact).where(Contact.platform_user_id == "456")
        )
        assert friend_contact is not None
        assert len(session.scalars(select(Contact)).all()) == 2
        sessions = session.scalars(
            select(ImportSession).order_by(ImportSession.id)
        ).all()
        assert [item.platform for item in sessions] == ["facebook", "facebook"]
        assert [
            (item.status, item.total_messages, item.inserted_messages, item.skipped_messages)
            for item in sessions
        ] == [("completed", 2, 2, 0), ("completed", 2, 0, 2)]


def test_facebook_import_rolls_back_after_database_failure(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'facebook-rollback.db'}")
    _create_import_tables(engine)
    archive_path = tmp_path / "facebook.zip"
    _write_archive(archive_path)

    def fail_insert(*args):
        assert len(args) == 2
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(facebook_importer, "insert_message_batch", fail_insert)
    with Session(engine) as session:
        try:
            facebook_importer.import_facebook_export(archive_path, session=session)
        except RuntimeError as exc:
            assert str(exc) == "synthetic database failure"
        else:
            raise AssertionError("expected the import to fail")

        assert session.scalar(select(Account)) is None
        assert session.scalar(select(ImportSession)) is None

    engine.dispose()


def test_facebook_import_keeps_direction_unknown_without_profile_identity(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'facebook-no-profile.db'}")
    _create_import_tables(engine)
    archive_path = tmp_path / "facebook-no-profile.zip"
    _write_archive(archive_path, include_profile=False)

    with Session(engine) as session:
        facebook_importer.import_facebook_export(archive_path, session=session)

        messages = session.scalars(
            select(Message).order_by(Message.message_id)
        ).all()
        assert [message.is_outgoing for message in messages] == [None, None]
        assert all(message.sender_contact_id is None for message in messages)
        chat = session.scalar(select(Chat))
        assert chat is not None and chat.title == "Synthetic conversation"
    engine.dispose()


def test_facebook_import_keeps_existing_messages_when_older_history_is_added(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'facebook-incremental.db'}")
    _create_import_tables(engine)
    first_archive = tmp_path / "facebook-first.zip"
    later_archive = tmp_path / "facebook-later.zip"
    _write_archive(first_archive)
    _write_archive(
        later_archive,
        extra_messages=[
            {
                "sender_name": "Synthetic Friend",
                "sender_id": "friend-456",
                "timestamp_ms": 1_600_000_000_000,
                "content": "older synthetic message",
            }
        ],
    )

    with Session(engine) as session:
        first = facebook_importer.import_facebook_export(first_archive, session=session)
        original_ids = {
            message.text_content: message.message_id
            for message in session.scalars(select(Message)).all()
        }
        second = facebook_importer.import_facebook_export(later_archive, session=session)
        imported_messages = session.scalars(select(Message)).all()

        assert first["inserted_messages"] == 2
        assert second["total_messages"] == 3
        assert second["inserted_messages"] == 1
        assert second["skipped_messages"] == 2
        assert len(imported_messages) == 3
        assert {
            message.text_content: message.message_id
            for message in imported_messages
            if message.text_content in original_ids
        } == original_ids

    engine.dispose()
