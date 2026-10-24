import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "c9f47a61d2e8_remove_source_message_id.py"
)
SPEC = importlib.util.spec_from_file_location(
    "remove_source_message_id_migration",
    MIGRATION_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_remove_source_message_id_preserves_messages_and_can_be_reversed():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, "
                "message_id VARCHAR(100), source_message_id VARCHAR(200), "
                "source_record_key VARCHAR(64), text_content TEXT, "
                "CONSTRAINT uq_messages_chat_message_id UNIQUE(chat_id, message_id), "
                "CONSTRAINT uq_messages_chat_source_id "
                "UNIQUE(chat_id, source_message_id), "
                "CONSTRAINT uq_messages_chat_source_record_key "
                "UNIQUE(chat_id, source_record_key))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO messages "
                "(id, chat_id, message_id, source_message_id, source_record_key, "
                "text_content) "
                "VALUES (1, 2, 'message-3', 'source-4', 'record-5', 'preserved')"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        columns = {
            column._mapping["name"]
            for column in connection.execute(text("PRAGMA table_info('messages')"))
        }
        assert "source_message_id" not in columns
        assert connection.execute(
            text(
                "SELECT message_id, source_record_key, text_content "
                "FROM messages WHERE id = 1"
            )
        ).one() == ("message-3", "record-5", "preserved")

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()

        assert connection.execute(
            text("SELECT source_message_id FROM messages WHERE id = 1")
        ).scalar_one() is None

    engine.dispose()
