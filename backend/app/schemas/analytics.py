from datetime import datetime
from typing import Literal

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


CommunicationBalanceClassification = Literal[
    "balanced",
    "mostly_owner",
    "mostly_contact",
    "strongly_owner",
    "strongly_contact",
    "insufficient_data",
]


class CommunicationBalanceContact(BaseModel):
    account_id: int = Field(description="Internal Telegram account ID.")
    contact_id: int = Field(description="Stable account-local contact ID.")
    telegram_user_id: str = Field(description="Matched Telegram user ID.")
    display_name: str | None = Field(description="Contact display name, when available.")
    owner_message_count: int = Field(
        description="Ordinary messages sent by the owner with known direction."
    )
    contact_message_count: int = Field(
        description="Ordinary messages sent by the contact with known direction."
    )
    total_message_count: int = Field(
        description="Known-direction ordinary messages; message counts are secondary context."
    )
    excluded_unknown_direction_message_count: int = Field(
        description="Ordinary messages in the eligible private chat whose sender direction is ambiguous."
    )
    owner_text_length: int = Field(
        description="Unicode code points in normalized text sent by the owner."
    )
    contact_text_length: int = Field(
        description="Unicode code points in normalized text sent by the contact."
    )
    total_text_length: int = Field(
        description="Owner plus contact text characters included in the balance."
    )
    owner_text_share: float | None = Field(
        description="Owner text length divided by total text length, or null when total text is zero."
    )
    contact_text_share: float | None = Field(
        description="Contact text length divided by total text length, or null when total text is zero."
    )
    absolute_share_difference: float | None = Field(
        description="Absolute difference between text shares, or null when total text is zero."
    )
    owner_share_percentage: float | None = Field(
        description="Owner share on a 0–100 scale, or null when total text is zero."
    )
    contact_share_percentage: float | None = Field(
        description="Contact share on a 0–100 scale, or null when total text is zero."
    )
    classification: CommunicationBalanceClassification
    first_message_at: datetime | None = Field(
        description="First known-direction ordinary message timestamp."
    )
    last_message_at: datetime | None = Field(
        description="Last known-direction ordinary message timestamp."
    )
    distinct_active_days: int = Field(
        description="Distinct UTC calendar days with known-direction ordinary messages."
    )


class CommunicationBalanceSummary(BaseModel):
    eligible_contacts: int = Field(description="Number of contacts with eligible private-chat data.")
    balanced_contacts: int
    mostly_owner_contacts: int
    mostly_contact_contacts: int
    strongly_owner_contacts: int
    strongly_contact_contacts: int
    insufficient_data_contacts: int
    owner_text_length: int = Field(description="Total owner text characters included.")
    contact_text_length: int = Field(description="Total contact text characters included.")
    total_text_length: int = Field(description="Total text characters included.")
    owner_message_count: int = Field(
        description="Known-direction ordinary messages sent by the owner."
    )
    contact_message_count: int = Field(
        description="Known-direction ordinary messages sent by contacts."
    )
    total_message_count: int = Field(
        description="Known-direction ordinary messages included in calculations."
    )
    excluded_unknown_direction_message_count: int = Field(
        description="Ordinary messages excluded due to unknown or inconsistent direction."
    )


class CommunicationBalanceStatistics(BaseModel):
    summary: CommunicationBalanceSummary
    contacts: list[CommunicationBalanceContact]