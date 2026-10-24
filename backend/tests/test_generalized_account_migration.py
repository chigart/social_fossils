import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "6a81c2f9d437_generalize_account_and_chat_ids.py"
)
SPEC = importlib.util.spec_from_file_location(
    "generalized_account_migration",
    MIGRATION_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_migration_renames_account_and_chat_ids_and_preserves_rows():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE telegram_accounts ("
                "id INTEGER PRIMARY KEY, platform VARCHAR(50), "
                "name VARCHAR(200), username VARCHAR(100), "
                "telegram_user_id VARCHAR(100), platform_user_id VARCHAR(100))"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX ix_telegram_accounts_platform "
                "ON telegram_accounts (platform)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE chats ("
                "id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, "
                "platform VARCHAR(50), telegram_chat_id VARCHAR(100), "
                "platform_chat_id VARCHAR(500), chat_type VARCHAR(50), "
                "title VARCHAR(300), "
                "CONSTRAINT uq_chats_account_telegram_id "
                "UNIQUE(account_id, telegram_chat_id), "
                "CONSTRAINT uq_chats_account_platform_id "
                "UNIQUE(account_id, platform_chat_id), "
                "FOREIGN KEY(account_id) REFERENCES telegram_accounts(id))"
            )
        )
        for table in ("contacts", "import_sessions", "upload_jobs"):
            connection.execute(
                text(
                    f"CREATE TABLE {table} ("
                    "id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, "
                    "FOREIGN KEY(account_id) REFERENCES telegram_accounts(id))"
                )
            )
        connection.execute(
            text(
                "INSERT INTO telegram_accounts "
                "(id, platform, name, username, telegram_user_id, platform_user_id) "
                "VALUES (1, 'telegram', 'Owner', 'owner', 'user-1', 'user-1'), "
                "(2, 'instagram', 'Instagram Owner', 'insta', NULL, 'insta')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO chats "
                "(id, account_id, platform, telegram_chat_id, platform_chat_id, "
                "chat_type, title) VALUES "
                "(10, 1, 'telegram', 'chat-10', 'chat-10', 'personal_chat', 'Telegram'), "
                "(20, 2, 'instagram', NULL, 'inbox/thread_20', 'personal_chat', 'Instagram')"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.upgrade()

        accounts = connection.execute(
            text(
                "SELECT id, platform, name, username, platform_user_id "
                "FROM account ORDER BY id"
            )
        ).all()
        chats = connection.execute(
            text(
                "SELECT id, account_id, chat_id FROM chats ORDER BY id"
            )
        ).all()
        assert accounts == [
            (1, "telegram", "Owner", "owner", "user-1"),
            (2, "instagram", "Instagram Owner", "insta", "insta"),
        ]
        assert chats == [(10, 1, "chat-10"), (20, 2, "inbox/thread_20")]
        for table in ("chats", "contacts", "import_sessions", "upload_jobs"):
            foreign_keys = connection.execute(
                text(f"PRAGMA foreign_key_list({table})")
            ).all()
            assert foreign_keys[0][2] == "account"
        chat_schema = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE name = 'chats'")
        ).scalar_one()
        assert "uq_chats_account_chat_id" in chat_schema

        with Operations.context(MigrationContext.configure(connection)):
            MIGRATION.downgrade()

        assert connection.execute(
            text(
                "SELECT telegram_user_id FROM telegram_accounts WHERE id = 1"
            )
        ).scalar_one() == "user-1"
        assert connection.execute(
            text(
                "SELECT telegram_chat_id FROM chats WHERE id = 10"
            )
        ).scalar_one() == "chat-10"

    engine.dispose()
