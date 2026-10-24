import json
from zipfile import ZipFile

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app import instagram_importer
from app.routers.analytics_overview import get_contact_statistics
from app.telegram_importer import import_source_export
from app.models import (
    CanonicalIdentity,
    Chat,
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
                "platform_user_id VARCHAR(100), identity_group_id INTEGER, "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(platform, platform_user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE contacts ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, "
                "platform VARCHAR(50), "
                "platform_user_id VARCHAR(100), source_contact_key VARCHAR(64), "
                "canonical_identity_id INTEGER, "
                "display_name VARCHAR(300), username VARCHAR(100), "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(account_id, platform_user_id), "
                "UNIQUE(account_id, source_contact_key))"
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
                "source_record_key VARCHAR(64), "
                "sender_id VARCHAR(100), "
                "sender_contact_id INTEGER, sender_name VARCHAR(300), "
                "is_outgoing BOOLEAN, message_date DATETIME, message_type VARCHAR(50), "
                "text_content TEXT, reply_to_telegram_message_id VARCHAR(100), "
                "source_reply_id VARCHAR(200), raw_payload JSON, "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
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
                                "User ID": {"value": "owner-123"},
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
                            "is_outgoing": False,
                        },
                        {
                            "message_id": "instagram-message-2",
                            "sender_id": "123",
                            "sender_name": "Synthetic sender",
                            "timestamp_ms": 1_700_000_000_456,
                            "content": "synthetic identified message",
                        },
                        {
                            "sender_id": "owner-123",
                            "sender_name": "Synthetic Owner",
                            "timestamp_ms": 1_700_000_000_789,
                            "content": "synthetic outgoing message",
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
        account = Account(
            platform="instagram",
            name="Synthetic Owner",
            username="synthetic_owner",
            platform_user_id="owner-123",
        )
        session.add(account)
        session.flush()
        session.add(
            Chat(
                account_id=account.id,
                platform="instagram",
                chat_id="inbox/example_123",
                chat_type="personal_chat",
                title=None,
            )
        )
        preserved_contact = Contact(
            account_id=account.id,
            platform="instagram",
            platform_user_id="456",
            canonical_identity_id=None,
            display_name="Contact from another export",
        )
        session.add(preserved_contact)
        session.commit()

        first = instagram_importer.import_instagram_export(
            archive_path,
            session=session,
        )
        idless_message = session.scalar(
            select(Message).where(Message.message_id == "1")
        )
        assert idless_message is not None
        assert idless_message.sender_id == "123"
        assert idless_message.sender_contact_id is not None
        idless_message.sender_id = None
        idless_message.sender_contact_id = None
        idless_message.message_id = None
        session.flush()
        second = import_source_export(
            "instagram",
            archive_path,
            session=session,
        )

        assert first["platform"] == "instagram"
        assert first["inserted_messages"] == 3
        assert first["inserted_contacts"] == 2
        assert first["total_contacts"] == 2
        assert second["inserted_messages"] == 0
        assert second["inserted_contacts"] == 0
        assert second["skipped_messages"] == 3

        account = session.scalar(select(Account))
        messages = session.scalars(select(Message)).all()
        chat = session.scalar(select(Chat))
        identified_message = session.scalar(
            select(Message).where(Message.message_id == "2")
        )
        contact = session.scalar(
            select(Contact).where(
                Contact.platform_user_id == "123"
            )
        )
        identity = session.scalar(select(CanonicalIdentity))
        import_sessions = session.scalars(select(ImportSession)).all()
        assert account is not None
        assert account.platform == "instagram"
        assert account.platform_user_id == "owner-123"
        assert account.username == "synthetic_owner"
        assert account.name == "Synthetic Owner"
        assert len(messages) == 3
        assert chat is not None and chat.chat_id == "123"
        assert contact is not None
        idless_message = next(
            message for message in messages if message.message_id == "1"
        )
        assert idless_message.platform == "instagram"
        assert idless_message.source_record_key
        assert idless_message.message_id == "1"
        assert idless_message.sender_id == "123"
        assert idless_message.sender_contact_id == contact.id
        assert idless_message.is_outgoing is False
        assert idless_message.raw_payload["content"] == "synthetic private text"
        assert identified_message is not None
        assert identified_message.message_id == "2"
        assert identified_message.sender_id == "123"
        assert identified_message.sender_contact_id == contact.id
        assert identified_message.sender_contact_id == contact.id
        outgoing_message = session.scalar(
            select(Message).where(Message.message_id == "3")
        )
        owner_contact = session.scalar(
            select(Contact).where(Contact.platform_user_id == "owner-123")
        )
        assert outgoing_message is not None
        assert owner_contact is not None
        assert outgoing_message.sender_id == "owner-123"
        assert outgoing_message.sender_contact_id == owner_contact.id
        assert outgoing_message.is_outgoing is True
        assert contact.platform == "instagram"
        assert contact.platform_user_id == "123"
        assert contact.username == "example"
        assert identity is not None and identity.platform == "instagram"
        contacts = session.scalars(select(Contact)).all()
        assert len(contacts) == 3
        assert preserved_contact in contacts
        assert contact.display_name == "Synthetic thread"
        assert len(import_sessions) == 2
        assert all(item.platform == "instagram" for item in import_sessions)

        contact_statistics = get_contact_statistics(session)
        peer_statistics = next(
            row for row in contact_statistics if row.platform_user_id == "123"
        )
        assert peer_statistics.display_name == "Synthetic thread"
        assert peer_statistics.total_messages_sent == 2
        assert peer_statistics.ordinary_messages_sent == 2
        assert all(row.total_messages_sent != 3 for row in contact_statistics)
        assert all(row.platform_user_id is not None for row in contact_statistics)

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
