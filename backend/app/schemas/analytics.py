from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
    ordinary_messages: int = Field(
        description="Rows whose message_type is exactly 'message'."
    )
    service_messages: int = Field(
        description="Rows whose message_type is exactly 'service'."
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
        description="Identifiable contacts in private chats with exactly one non-owner sender."
    )
    meaningful_historical_contacts: int
    currently_inactive_contacts: int
    declining_activity_contacts: int
    insufficient_data_contacts: int


class ForgottenContactsStatistics(BaseModel):
    summary: ForgottenContactsSummary
    contacts: list[ForgottenContact]


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
    scope: Literal["owner", "contact"]
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


class WordFrequency(BaseModel):
    word: str
    count: int


class EmojiFrequency(BaseModel):
    emoji: str
    count: int


class ChatInsightSender(BaseModel):
    sender_id: str | None
    display_name: str
    message_count: int
    text_length: int = Field(
        description="Unicode code points in normalized ordinary-message text."
    )
    popular_words: list[WordFrequency]
    popular_emojis: list[EmojiFrequency]


class ReactionReactor(BaseModel):
    reactor_id: str
    display_name: str
    reaction_count: int = Field(
        description="Observed reaction entries in the source payload's reactor lists."
    )
    popular_emojis: list[EmojiFrequency]


class ReactionAuthorPair(BaseModel):
    reactor_id: str
    reactor_name: str
    author_id: str
    author_name: str
    observed_reaction_count: int = Field(
        description="Observed reaction entries on this author's messages."
    )
    messages_with_observed_reaction_count: int = Field(
        description="Distinct author messages with at least one observed reaction from this reactor."
    )
    author_message_count: int = Field(
        description="All ordinary messages authored by this sender in this chat."
    )
    observed_message_percentage: float = Field(
        description="Observed reacted-to messages divided by author message count; a lower bound when recent reactors are incomplete."
    )


class ReplyTempoStatistics(BaseModel):
    reply_reference_count: int = Field(
        description="Ordinary messages that reference another message in this chat."
    )
    measured_reply_count: int = Field(
        description="References resolved to a dated ordinary message by a different identified sender."
    )
    median_response_seconds: float | None = Field(
        description="Median elapsed time from the referenced message to its reply, for measured replies."
    )


class ConversationParticipantCount(BaseModel):
    sender_id: str | None
    display_name: str
    count: int


class MessageTypeCount(BaseModel):
    category: str
    count: int
    with_text_count: int = Field(
        description="Messages in this category that also contain normalized text."
    )
    senders: list[ConversationParticipantCount] = Field(
        description="Top senders for this message category, ranked by message count."
    )


class ConversationHandoffCount(BaseModel):
    previous_closer_id: str
    previous_closer_name: str
    next_opener_id: str
    next_opener_name: str
    count: int


class ConversationActivityStatistics(BaseModel):
    session_gap_hours: int
    session_count: int = Field(
        description="Dated ordinary-message sessions separated by the configured inactivity gap."
    )
    messages_without_timestamp_count: int
    sender_transition_count: int = Field(
        description="Adjacent, identified sender pairs within sessions."
    )
    sender_switch_count: int = Field(
        description="Adjacent, identified messages in a session written by different senders."
    )
    sender_switch_percentage: float
    longest_turn_taking_streak: int = Field(
        description="Longest sequence of dated messages where every adjacent identified sender switched."
    )
    attributed_handoff_count: int = Field(
        description="Adjacent dated conversation sessions with identified previous closers and next openers."
    )
    unattributed_handoff_count: int
    opening_senders: list[ConversationParticipantCount]
    closing_senders: list[ConversationParticipantCount]
    handoffs: list[ConversationHandoffCount]


class ChatInsightsStatistics(BaseModel):
    chat_id: int
    account_id: int
    platform: str
    source_account_label: str
    title: str | None
    chat_type: str
    ordinary_message_count: int
    text_length: int = Field(
        description="Unicode code points in normalized ordinary-message text."
    )
    popular_words: list[WordFrequency]
    popular_emojis: list[EmojiFrequency]
    senders: list[ChatInsightSender]
    reaction_count: int = Field(
        description="Sum of full per-message emoji reaction counts available in source payloads."
    )
    reaction_emojis: list[EmojiFrequency]
    reactors: list[ReactionReactor] = Field(
        description="Per-reactor statistics observed in source payloads."
    )
    reactor_author_pairs: list[ReactionAuthorPair] = Field(
        description="Observed reactor-to-author coverage, not exhaustive when recent lists are incomplete."
    )
    message_type_breakdown: list[MessageTypeCount]
    reply_tempo: ReplyTempoStatistics
    conversation_activity: ConversationActivityStatistics


class ChatInsightsResponse(BaseModel):
    chats: list[ChatInsightsStatistics]