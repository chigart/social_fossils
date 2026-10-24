import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "b7f2c4d91a63_rename_message_platform_columns.py"
)
SPEC = importlib.util.spec_from_file_location("message_columns_migration", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_message_column_migration_renames_columns_and_preserves_values():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, "
                "telegram_message_id VARCHAR(100), "
                "sender_telegram_id VARCHAR(100), "
                "CONSTRAINT uq_messages_chat_telegram_id "
                "UNIQUE(chat_id, telegram_message_id))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO messages "
                "(id, chat_id, telegram_message_id, sender_telegram_id) "
                "VALUES (1, 2, 'message-3', 'user-4')"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        columns = {
            column._mapping["name"]
            for column in connection.execute(text("PRAGMA table_info('messages')"))
        }
        assert {"message_id", "sender_id"} <= columns
        assert "telegram_message_id" not in columns
        assert "sender_telegram_id" not in columns
        assert connection.execute(
            text("SELECT message_id, sender_id FROM messages WHERE id = 1")
        ).one() == ("message-3", "user-4")

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()

        assert connection.execute(
            text(
                "SELECT telegram_message_id, sender_telegram_id "
                "FROM messages WHERE id = 1"
            )
        ).one() == ("message-3", "user-4")

    engine.dispose()
