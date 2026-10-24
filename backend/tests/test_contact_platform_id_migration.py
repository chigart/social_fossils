import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "4cba6d2e901f_remove_legacy_contact_telegram_id.py"
)
SPEC = importlib.util.spec_from_file_location(
    "contact_platform_id_migration",
    MIGRATION_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_contact_platform_id_migration_preserves_telegram_ids():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE contacts ("
                "id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, "
                "platform VARCHAR(50) NOT NULL, "
                "platform_user_id VARCHAR(100), "
                "telegram_user_id VARCHAR(100), "
                "CONSTRAINT uq_contacts_account_telegram_id "
                "UNIQUE (account_id, telegram_user_id), "
                "CONSTRAINT uq_contacts_account_platform_id "
                "UNIQUE (account_id, platform_user_id))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO contacts "
                "(id, account_id, platform, platform_user_id, telegram_user_id) "
                "VALUES "
                "(1, 10, 'telegram', NULL, 'telegram-1'), "
                "(2, 20, 'instagram', 'instagram-1', NULL)"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        rows = connection.execute(
            text(
                "SELECT id, platform, platform_user_id FROM contacts ORDER BY id"
            )
        ).all()
        columns = {column["name"] for column in inspect(connection).get_columns("contacts")}

        assert [tuple(row) for row in rows] == [
            (1, "telegram", "telegram-1"),
            (2, "instagram", "instagram-1"),
        ]
        assert "telegram_user_id" not in columns

    engine.dispose()
