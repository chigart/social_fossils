import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "7a31c9e4b2f0_allow_multiple_identities_per_platform.py"
)
SPEC = importlib.util.spec_from_file_location(
    "multi_account_identity_migration",
    MIGRATION_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_migration_allows_multiple_identities_from_one_platform_per_group():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE canonical_identities ("
                "id INTEGER PRIMARY KEY, platform VARCHAR(50) NOT NULL, "
                "platform_user_id VARCHAR(100) NOT NULL, "
                "identity_group_id INTEGER, "
                "CONSTRAINT uq_canonical_identities_group_platform "
                "UNIQUE (identity_group_id, platform))"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        connection.execute(
            text(
                "INSERT INTO canonical_identities "
                "(id, platform, platform_user_id, identity_group_id) "
                "VALUES (1, 'telegram', 'telegram-1', 7), "
                "(2, 'telegram', 'telegram-2', 7)"
            )
        )
        assert connection.execute(
            text("SELECT count(*) FROM canonical_identities")
        ).scalar_one() == 2

    engine.dispose()
