from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analytics_common import PaginationMetadata, SearchOption

CommunicationBalanceClassification = Literal[
    "balanced",
    "mostly_owner",
    "mostly_contact",
    "strongly_owner",
    "strongly_contact",
    "insufficient_data",
]


ForgottenContactClassification = Literal[
    "insufficient_data",
    "inactive",
    "activity_declined",
    "active",
]

ForgottenContactEvidenceStatus = Literal[
    "reliable_baseline",
    "insufficient_history",
    "insufficient_baseline",
    "ambiguous_direction",
]


class CloseFriendsTimelineYear(BaseModel):
    year: int
    close_friend_count: int = Field(
        description="Close-qualified contacts in the UTC calendar year."
    )


class CloseFriendsTimelineStatistics(BaseModel):
    years: list[CloseFriendsTimelineYear]


class OwnerReplyTimelineYear(BaseModel):
    year: int = Field(description="UTC calendar year of the owner reply.")
    average_response_seconds: float | None = Field(
        description=(
            "Mean elapsed seconds for measured owner replies in this year, or "
            "null when the year has no measured replies."
        )
    )


class OwnerReplyTimelineStatistics(BaseModel):
    years: list[OwnerReplyTimelineYear]


class ForgottenContactMonthlyActivity(BaseModel):
    month: str = Field(description="UTC calendar month in YYYY-MM format.")
    owner_message_count: int
    contact_message_count: int
    total_message_count: int


class ForgottenContact(BaseModel):
    account_id: int | None = Field(
        description="Single source account ID, or null when combined across accounts."
    )
    contact_id: int = Field(description="Stable account-local contact ID.")
    canonical_identity_id: int | None = Field(
        description="Representative platform identity ID, when available."
    )
    identity_group_id: int | None = Field(
        default=None,
        description="Explicit cross-platform identity group, when linked.",
    )
    platforms: list[str] = Field(
        description="Platforms represented by this identity group."
    )
    source_account_ids: list[int] = Field(
        description="Source accounts contributing messages to this contact."
    )
    source_account_labels: list[str] = Field(
        description="Source-account usernames or account names for contributing sources."
    )
    source_contact_ids: list[int] = Field(
        description="Account-local contact rows contributing to this contact."
    )
    platform_user_ids: list[str] = Field(
        description="Known platform user IDs represented by this contact group."
    )
    display_name: str | None
    interaction_chat_count: int = Field(
        description="Distinct chats contributing to this interaction history."
    )
    first_message_at: datetime | None
    last_message_at: datetime | None
    days_since_last_communication: int | None
    owner_message_count: int = Field(
        description="Ordinary messages with reliable owner direction across all dates."
    )
    contact_message_count: int = Field(
        description="Ordinary messages with reliable contact direction across all dates."
    )
    total_message_count: int = Field(
        description="Known-direction ordinary messages across all dates."
    )
    excluded_ambiguous_message_count: int = Field(
        description="Ordinary messages not counted because sender identity or direction was ambiguous."
    )
    owner_text_length: int
    contact_text_length: int
    total_text_length: int
    distinct_active_days: int
    historical_message_count: int = Field(
        description="Known-direction ordinary messages before the recent window."
    )
    historical_active_days: int
    historical_active_month_count: int
    historical_activity_by_month: list[ForgottenContactMonthlyActivity]
    recent_activity_by_month: list[ForgottenContactMonthlyActivity]
    recent_owner_message_count: int
    recent_contact_message_count: int
    recent_message_count: int
    historical_monthly_baseline: float | None = Field(
        description="Historical messages per FORGOTTEN_RECENT_MONTH_DAYS days over the dated historical activity span."
    )
    recent_monthly_activity: float
    activity_decline_percentage: float | None = Field(
        description="Recent rate decline versus historical baseline, capped to 0-100; null without a reliable baseline."
    )
    classification: ForgottenContactClassification
    evidence_status: ForgottenContactEvidenceStatus
    ranking_score: float | None = Field(
        description="0-100 ranking score; null when historical evidence or direction is insufficient."
    )


class ForgottenContactsSummary(BaseModel):
    scope: Literal["combined_owner"] = "combined_owner"
    source_account_count: int = Field(
        description="Number of imported source accounts included in the combined scope."
    )
    eligible_contacts: int = Field(
        description="Identifiable one-to-one contacts in private scope, or group participants in group scope."
    )
    meaningful_historical_contacts: int
    currently_inactive_contacts: int
    declining_activity_contacts: int
    insufficient_data_contacts: int


class ForgottenSearchOption(SearchOption):
    contact_id: int


class ForgottenContactsStatistics(BaseModel):
    summary: ForgottenContactsSummary
    contacts: list[ForgottenContact]
    pagination: PaginationMetadata
    options: list[ForgottenSearchOption] = Field(default_factory=list)


class CommunicationBalanceContact(BaseModel):
    account_id: int | None = Field(
        description="Single source account ID, or null when combined across accounts."
    )
    contact_id: int = Field(description="Stable account-local contact ID.")
    canonical_identity_id: int | None = Field(
        description="Representative platform identity ID, when available."
    )
    identity_group_id: int | None = Field(
        default=None,
        description="Explicit cross-platform identity group, when linked.",
    )
    platforms: list[str] = Field(
        description="Platforms represented by this identity group."
    )
    source_account_ids: list[int] = Field(
        description="Source accounts contributing messages to this contact."
    )
    source_account_labels: list[str] = Field(
        description="Source-account usernames or account names for contributing sources."
    )
    source_contact_ids: list[int] = Field(
        description="Account-local contact rows contributing to this contact."
    )
    platform_user_ids: list[str] = Field(
        description="Known platform user IDs represented by this contact group."
    )
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
    pagination: PaginationMetadata
    options: list[SearchOption] = Field(default_factory=list)
