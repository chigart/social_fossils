import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "2d91a5c7e4b0_drop_unused_chat_members.py"
)
SPEC = importlib.util.spec_from_file_location("drop_chat_members_migration", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_migration_drops_chat_members_and_downgrade_restores_schema():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE chats (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE contacts (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE chat_members ("
                "id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, "
                "telegram_user_id VARCHAR(100) NOT NULL, contact_id INTEGER, "
                "display_name VARCHAR(300), is_self BOOLEAN NOT NULL DEFAULT false, "
                "UNIQUE(chat_id, telegram_user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX ix_chat_members_chat_id ON chat_members (chat_id)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO chat_members (id, chat_id, telegram_user_id) "
                "VALUES (1, 1, 'synthetic-user')"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        assert "chat_members" not in inspect(connection).get_table_names()

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()

        assert "chat_members" in inspect(connection).get_table_names()
        assert inspect(connection).get_indexes("chat_members") == [
            {
                "name": "ix_chat_members_chat_id",
                "column_names": ["chat_id"],
                "unique": 0,
                "dialect_options": {},
            }
        ]

    engine.dispose()
