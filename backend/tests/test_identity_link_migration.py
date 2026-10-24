import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "5e7b3f0c91a2_add_explicit_identity_links.py"
)
SPEC = importlib.util.spec_from_file_location("identity_link_migration", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_identity_link_migration_preserves_existing_identities_and_contacts():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE canonical_identities ("
                "id INTEGER PRIMARY KEY, platform VARCHAR(50) NOT NULL, "
                "platform_user_id VARCHAR(100) NOT NULL, "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                "UNIQUE(platform, platform_user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE contacts ("
                "id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, "
                "platform VARCHAR(50) NOT NULL, platform_user_id VARCHAR(100), "
                "display_name VARCHAR(300))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO canonical_identities "
                "(id, platform, platform_user_id) VALUES (1, 'telegram', 'user-1')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO contacts "
                "(id, account_id, platform, platform_user_id, display_name) "
                "VALUES (2, 3, 'telegram', 'user-1', 'Synthetic contact')"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        identity = connection.execute(
            text(
                "SELECT id, platform, platform_user_id, identity_group_id "
                "FROM canonical_identities"
            )
        ).one()
        contact = connection.execute(
            text(
                "SELECT id, account_id, platform_user_id, display_name, "
                "source_contact_key FROM contacts"
            )
        ).one()
        assert tuple(identity) == (1, "telegram", "user-1", None)
        assert tuple(contact) == (2, 3, "user-1", "Synthetic contact", None)
        assert connection.execute(
            text("SELECT count(*) FROM identity_link_events")
        ).scalar_one() == 0

    engine.dispose()
