from datetime import datetime

from pydantic import BaseModel, Field


class OverviewStatistics(BaseModel):
    total_imported_accounts: int = Field(
        description="Number of Telegram account rows in the database."
    )
    total_chats: int = Field(description="Number of chat rows across all accounts.")
    total_messages: int = Field(
        description="All message rows, including service events and other stored types."
    )
    total_ordinary_messages: int = Field(
        description="Rows whose message_type is exactly 'message'."
    )
    total_service_messages: int = Field(
        description="Rows whose message_type is exactly 'service'."
    )
    earliest_message_timestamp: datetime | None = Field(
        description="Earliest non-null message timestamp, or null when unavailable."
    )
    latest_message_timestamp: datetime | None = Field(
        description="Latest non-null message timestamp, or null when unavailable."
    )


class ChatStatistics(BaseModel):
    chat_id: int = Field(description="Internal database chat ID.")
    telegram_chat_id: str = Field(description="Chat ID from the Telegram export.")
    title: str | None
    chat_type: str
    total_messages: int = Field(
        description="All stored message types; zero when the chat has no messages."
    )
    ordinary_messages: int = Field(
        description="Rows whose message_type is exactly 'message'."
    )
    service_messages: int = Field(
        description="Rows whose message_type is exactly 'service'."
    )
    earliest_message_timestamp: datetime | None
    latest_message_timestamp: datetime | None
    distinct_identified_senders: int = Field(
        description="Count of distinct non-null stored sender Telegram IDs."
    )


class ContactStatistics(BaseModel):
    account_id: int = Field(description="Internal account ID for this sender group.")
    contact_id: int | None = Field(
        description="Matching account-local contact ID, or null when unlinked."
    )
    telegram_user_id: str | None = Field(
        description="Stored sender Telegram ID, or null for unidentified senders."
    )
    display_name: str | None = Field(
        description="Contact display name when the Telegram ID resolves to a contact."
    )
    total_messages_sent: int = Field(
        description="Incoming message rows attributed to this sender, all types."
    )
    ordinary_messages_sent: int = Field(
        description="Attributed rows whose message_type is exactly 'message'."
    )
    service_events_attributed: int = Field(
        description="Attributed rows whose message_type is exactly 'service'."
    )