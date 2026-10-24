import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "a31b9fc812de_use_sender_id_for_all_platforms.py"
)
SPEC = importlib.util.spec_from_file_location("sender_id_migration", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_sender_id_migration_preserves_identifiers_and_drops_duplicate_column():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, "
                "sender_id VARCHAR(100), "
                "sender_platform_user_id VARCHAR(100))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO messages (id, sender_id, sender_platform_user_id) "
                "VALUES (1, 'telegram-id', 'telegram-id'), "
                "(2, NULL, 'instagram-id'), "
                "(3, 'existing-id', NULL)"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        assert connection.execute(
            text("SELECT id, sender_id FROM messages ORDER BY id")
        ).all() == [
            (1, "telegram-id"),
            (2, "instagram-id"),
            (3, "existing-id"),
        ]
        columns = {
            row._mapping["name"]
            for row in connection.execute(text("PRAGMA table_info('messages')"))
        }
        assert "sender_id" in columns
        assert "sender_platform_user_id" not in columns

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()

        assert connection.execute(
            text(
                "SELECT sender_id, sender_platform_user_id "
                "FROM messages WHERE id = 2"
            )
        ).one() == ("instagram-id", "instagram-id")

    engine.dispose()
