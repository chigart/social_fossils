import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "8d9af4113e72_add_platform_import_fields.py"
)
SPEC = importlib.util.spec_from_file_location("platform_import_migration", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_platform_migration_preserves_telegram_identifiers_without_platform_defaults():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE telegram_accounts ("
                "id INTEGER PRIMARY KEY, name VARCHAR(200), username VARCHAR(100), "
                "telegram_user_id VARCHAR(100))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE contacts ("
                "id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, "
                "telegram_user_id VARCHAR(100) NOT NULL, "
                "CONSTRAINT uq_contacts_account_telegram_id "
                "UNIQUE(account_id, telegram_user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE chats ("
                "id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, "
                "telegram_chat_id VARCHAR(100) NOT NULL, "
                "CONSTRAINT uq_chats_account_telegram_id "
                "UNIQUE(account_id, telegram_chat_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, "
                "telegram_message_id VARCHAR(100) NOT NULL, "
                "sender_telegram_id VARCHAR(100), "
                "reply_to_telegram_message_id VARCHAR(100), "
                "CONSTRAINT uq_messages_chat_telegram_id "
                "UNIQUE(chat_id, telegram_message_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE import_sessions ("
                "id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE upload_jobs ("
                "id INTEGER PRIMARY KEY, filename VARCHAR(500))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO telegram_accounts "
                "(id, name, username, telegram_user_id) "
                "VALUES (1, 'Owner', 'owner', 'user1')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO contacts (id, account_id, telegram_user_id) "
                "VALUES (1, 1, 'user2')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO chats (id, account_id, telegram_chat_id) "
                "VALUES (1, 1, 'chat3')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO messages "
                "(id, chat_id, telegram_message_id, sender_telegram_id, "
                "reply_to_telegram_message_id) "
                "VALUES (1, 1, 'message4', 'user2', 'message3')"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        assert connection.execute(
            text(
                "SELECT platform, platform_user_id, telegram_user_id "
                "FROM telegram_accounts WHERE id = 1"
            )
        ).one() == ("telegram", "user1", "user1")
        assert connection.execute(
            text(
                "SELECT platform, platform_user_id, telegram_user_id "
                "FROM contacts WHERE id = 1"
            )
        ).one() == ("telegram", "user2", "user2")
        assert connection.execute(
            text(
                "SELECT platform, platform_chat_id, telegram_chat_id "
                "FROM chats WHERE id = 1"
            )
        ).one() == ("telegram", "chat3", "chat3")
        assert connection.execute(
            text(
                "SELECT platform, source_message_id, sender_platform_user_id, "
                "source_reply_id FROM messages WHERE id = 1"
            )
        ).one() == ("telegram", "message4", "user2", "message3")
        for table in (
            "telegram_accounts",
            "contacts",
            "chats",
            "messages",
            "import_sessions",
            "upload_jobs",
        ):
            platform_column = next(
                column
                for column in connection.execute(
                    text(f"PRAGMA table_info('{table}')")
                )
                if column._mapping["name"] == "platform"
            )
            assert platform_column._mapping["dflt_value"] is None

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()

        assert connection.execute(
            text(
                "SELECT telegram_user_id FROM telegram_accounts WHERE id = 1"
            )
        ).scalar_one() == "user1"
        assert connection.execute(
            text(
                "SELECT telegram_message_id FROM messages WHERE id = 1"
            )
        ).scalar_one() == "message4"

    engine.dispose()
