import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "9a6f2d1c4b80_add_canonical_contact_identities.py"
)
SPEC = importlib.util.spec_from_file_location(
    "canonical_identity_migration",
    MIGRATION_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)

USERNAME_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "c1b82e7a3d46_add_telegram_account_username.py"
)
USERNAME_SPEC = importlib.util.spec_from_file_location(
    "telegram_account_username_migration",
    USERNAME_MIGRATION_PATH,
)
assert USERNAME_SPEC is not None and USERNAME_SPEC.loader is not None
USERNAME_MIGRATION = importlib.util.module_from_spec(USERNAME_SPEC)
USERNAME_SPEC.loader.exec_module(USERNAME_MIGRATION)


@pytest.mark.parametrize(
    "contact_rows",
    [
        [],
        [
            (10, 1, "user123", "Old display name"),
            (20, 2, "user123", "Updated display name"),
            (30, 2, "user456", None),
        ],
    ],
)
def test_migration_backfills_identities_and_preserves_contacts(contact_rows):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE contacts ("
                "id INTEGER PRIMARY KEY, "
                "account_id INTEGER NOT NULL, "
                "telegram_user_id VARCHAR(100) NOT NULL, "
                "display_name VARCHAR(300), "
                "CONSTRAINT uq_contacts_account_telegram_id "
                "UNIQUE (account_id, telegram_user_id))"
            )
        )
        for contact_id, account_id, user_id, display_name in contact_rows:
            connection.execute(
                text(
                    "INSERT INTO contacts "
                    "(id, account_id, telegram_user_id, display_name) "
                    "VALUES (:id, :account_id, :user_id, :display_name)"
                ),
                {
                    "id": contact_id,
                    "account_id": account_id,
                    "user_id": user_id,
                    "display_name": display_name,
                },
            )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        identities = connection.execute(
            text(
                "SELECT id, platform, platform_user_id "
                "FROM canonical_identities ORDER BY platform_user_id"
            )
        ).all()
        migrated_contacts = connection.execute(
            text(
                "SELECT id, account_id, telegram_user_id, canonical_identity_id "
                "FROM contacts ORDER BY id"
            )
        ).all()

        assert len(identities) == len({row[2] for row in contact_rows})
        assert [row[:3] for row in migrated_contacts] == [
            row[:3] for row in contact_rows
        ]
        identity_ids = {
            row.platform_user_id: row.id for row in identities
        }
        assert all(
            contact.canonical_identity_id
            == identity_ids[contact.telegram_user_id]
            for contact in migrated_contacts
        )
        assert all(identity.platform == "telegram" for identity in identities)

    engine.dispose()


def test_account_username_migration_preserves_existing_accounts():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE telegram_accounts ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(200) NOT NULL, "
                "telegram_user_id VARCHAR(100))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO telegram_accounts (id, name, telegram_user_id) "
                "VALUES (1, 'Existing account', 'user123')"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            USERNAME_MIGRATION.upgrade()

        account = connection.execute(
            text(
                "SELECT id, name, telegram_user_id, username "
                "FROM telegram_accounts"
            )
        ).one()
        assert tuple(account) == (1, "Existing account", "user123", None)

    engine.dispose()
