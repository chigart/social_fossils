import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Keep the application's unused default engine away from any configured database in tests.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE telegram_accounts ("
            "id INTEGER PRIMARY KEY, name VARCHAR(200), "
            "username VARCHAR(100), telegram_user_id VARCHAR(100))"
        ))
        connection.execute(text(
            "CREATE TABLE canonical_identities ("
            "id INTEGER PRIMARY KEY, platform VARCHAR(50), "
            "platform_user_id VARCHAR(100))"
        ))
        connection.execute(text(
            "CREATE TABLE contacts ("
            "id INTEGER PRIMARY KEY, account_id INTEGER, "
            "telegram_user_id VARCHAR(100), canonical_identity_id INTEGER, "
            "display_name VARCHAR(300))"
        ))
        connection.execute(text(
            "CREATE TABLE chats ("
            "id INTEGER PRIMARY KEY, account_id INTEGER, "
            "telegram_chat_id VARCHAR(100), title VARCHAR(300), "
            "chat_type VARCHAR(50))"
        ))
        connection.execute(text(
            "CREATE TABLE messages ("
            "id INTEGER PRIMARY KEY, chat_id INTEGER, "
            "telegram_message_id VARCHAR(100), "
            "sender_telegram_id VARCHAR(100), sender_contact_id INTEGER, "
            "sender_name VARCHAR(300), is_outgoing BOOLEAN, "
            "message_date DATETIME, message_type VARCHAR(50), "
            "text_content TEXT, reply_to_telegram_message_id VARCHAR(100), "
            "raw_payload JSON)"
        ))

    with Session(engine) as session:
        yield session
    engine.dispose()