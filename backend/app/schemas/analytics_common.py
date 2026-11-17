from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMetadata(BaseModel):
    page: int = Field(description="One-based result page.")
    page_size: int = Field(description="Maximum number of rows in this page.")
    total: int = Field(description="Total matching rows across all pages.")


class SearchOption(BaseModel):
    value: str
    label: str
    platforms: list[str]
    search_terms: list[str] = Field(default_factory=list)


class PaginatedItems(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMetadata
    options: list[SearchOption] = Field(
        default_factory=list,
        description="Lightweight options for searching the complete result set.",
    )


class ImportedAccountStatistics(BaseModel):
    id: int = Field(description="Internal database ID for the imported account.")
    platform: str = Field(description="Messaging platform for the imported account.")
    name: str = Field(description="Imported account name.")
    username: str | None = Field(description="Username for the imported account.")
    platform_user_id: str | None = Field(
        description="Account ID assigned by the messaging platform."
    )
    total_messages: int = Field(description="All stored messages for this account.")
    total_text_length: int = Field(
        description="Total characters in ordinary message text for this account."
    )
    total_contacts: int = Field(description="Contacts imported for this account.")
    earliest_message_timestamp: datetime | None
    latest_message_timestamp: datetime | None


class OverviewStatistics(BaseModel):
    total_imported_accounts: int = Field(
        description="Number of imported source-account rows in the database."
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
    imported_accounts: list[ImportedAccountStatistics] = Field(
        default_factory=list,
        description="Per-account message and contact totals, including empty accounts."
    )
    earliest_message_timestamp: datetime | None = Field(
        description="Earliest non-null message timestamp, or null when unavailable."
    )
    latest_message_timestamp: datetime | None = Field(
        description="Latest non-null message timestamp, or null when unavailable."
    )


class ChatStatistics(BaseModel):
    chat_id: int = Field(description="Internal database chat ID.")
    account_id: int = Field(
        description="Source account ID for this chat."
    )
    platform: str = Field(description="Messaging platform for this chat.")
    source_account_label: str = Field(
        description="Source-account username, or imported account name when no username exists."
    )
    platform_chat_id: str = Field(description="Chat ID from the source platform.")
    title: str | None
    chat_type: str
    total_messages: int = Field(
        description="All stored message types; zero when the chat has no messages."
    )
    text_length: int = Field(
        description="Total characters in ordinary message text for this chat."
    )
    ordinary_messages: int = Field(
        description="Rows whose message_type is exactly 'message'."
    )
    service_messages: int = Field(
        description="Rows whose message_type is exactly 'service'."
    )
    average_response_seconds: float | None = Field(
        default=None,
        description=(
            "Mean time from the owner's first message to the contact's first "
            "response within 12 hours in each measured 12-hour conversation "
            "session; omitted unless at least five sessions are measured."
        )
    )
    earliest_message_timestamp: datetime | None
    latest_message_timestamp: datetime | None
    distinct_identified_senders: int = Field(
        description="Count of distinct non-null platform-scoped sender IDs."
    )


class ContactAccountSource(BaseModel):
    platform: str
    label: str


class ContactStatistics(BaseModel):
    friend_statuses: list[Literal["Active", "Close", "exClose"]] = Field(
        default_factory=list,
        description=(
            "Current relationship signals. Active is independent and can appear "
            "alongside Close or exClose."
        ),
    )
    platforms: list[str] = Field(
        description="Platforms represented by this identity group."
    )
    account_id: int | None = Field(
        default=None,
        description="Single source account ID, or null when combined across accounts.",
    )
    identity_group_id: int | None = Field(
        default=None,
        description="Explicit cross-platform identity group, when linked.",
    )
    canonical_identity_id: int | None = Field(
        default=None,
        description="A platform identity ID for this group, when available."
    )
    source_account_ids: list[int] = Field(
        default_factory=list,
        description="Source accounts contributing messages to this group."
    )
    source_account_labels: list[str] = Field(
        default_factory=list,
        description="Usernames or account names for contributing sources."
    )
    source_accounts: list[ContactAccountSource] = Field(
        default_factory=list,
        description="Platform and label for each contributing source account."
    )
    source_contact_ids: list[int] = Field(
        default_factory=list,
        description="Account-local contact rows contributing to this group."
    )
    platform_user_ids: list[str] = Field(
        description="Known platform user IDs represented by this contact group."
    )
    display_name: str | None = Field(
        description="Contact display name when a source identity resolves to a contact."
    )
    total_messages_sent: int = Field(
        description="Incoming message rows attributed to this sender, all types."
    )
    personal_chat_messages_sent: int = Field(
        description="Incoming message rows attributed to this sender in one-to-one chats."
    )
    group_chat_messages_sent: int = Field(
        description="Incoming message rows attributed to this sender in non-one-to-one chats."
    )
    ordinary_messages_sent: int = Field(
        description="Attributed rows whose message_type is exactly 'message'."
    )
    service_events_attributed: int = Field(
        description="Attributed rows whose message_type is exactly 'service'."
    )
