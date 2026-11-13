from typing import Literal

from pydantic import BaseModel, Field

class CommunicationTimelineMonth(BaseModel):
    month: str = Field(description="UTC calendar month in YYYY-MM format.")
    ordinary_message_count: int = Field(
        description="Dated ordinary messages in this UTC month."
    )
    owner_message_count: int = Field(
        description="Dated ordinary messages reliably identified as owner-sent."
    )
    contact_message_count: int = Field(
        description="Dated ordinary messages reliably identified as contact-sent."
    )
    unknown_direction_message_count: int = Field(
        description="Dated ordinary messages whose sender direction is ambiguous."
    )
    active_days: int = Field(
        description="Distinct UTC dates with at least one dated ordinary message."
    )
    owner_active_days: int = Field(
        description="Distinct UTC dates with a reliably owner-sent message."
    )
    contact_active_days: int = Field(
        description="Distinct UTC dates with a reliably contact-sent message."
    )
    unknown_direction_active_days: int = Field(
        description="Distinct UTC dates with a message of unknown direction."
    )


class CommunicationTimelineSummary(BaseModel):
    scope: Literal["owner", "contact", "chat"]
    chat_id: int | None = Field(
        default=None,
        description="Selected chat ID for chat scope; null otherwise.",
    )
    identity_group_id: int | None = Field(
        default=None,
        description="Explicit identity group selected for contact scope, when linked.",
    )
    canonical_identity_id: int | None = Field(
        description="Selected canonical identity for contact scope; null for owner scope."
    )
    source_account_count: int = Field(
        description="Number of imported source accounts represented by this scope."
    )
    source_account_ids: list[int] = Field(
        description="Internal IDs of source accounts represented by this scope."
    )
    source_account_labels: list[str] = Field(
        description="Source-account usernames, or imported account names when unavailable."
    )
    source_contact_ids: list[int] = Field(
        description="Account-local contact rows mapped to the selected identity."
    )
    ordinary_message_count: int = Field(
        description="All ordinary messages in scope, including those without timestamps."
    )
    dated_ordinary_message_count: int = Field(
        description="Ordinary messages included in the monthly timeline."
    )
    undated_ordinary_message_count: int = Field(
        description="Ordinary messages with no timestamp; these are not assigned to a month."
    )
    owner_message_count: int = Field(
        description="All ordinary messages reliably identified as owner-sent."
    )
    contact_message_count: int = Field(
        description="All ordinary messages reliably identified as contact-sent."
    )
    unknown_direction_message_count: int = Field(
        description="All ordinary messages whose sender direction is ambiguous."
    )
    undated_owner_message_count: int = Field(
        description="Undated ordinary messages reliably identified as owner-sent."
    )
    undated_contact_message_count: int = Field(
        description="Undated ordinary messages reliably identified as contact-sent."
    )
    undated_unknown_direction_message_count: int = Field(
        description="Undated ordinary messages whose sender direction is ambiguous."
    )


class CommunicationTimelineStatistics(BaseModel):
    summary: CommunicationTimelineSummary
    months: list[CommunicationTimelineMonth]


