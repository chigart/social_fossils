from pydantic import BaseModel, Field

from app.schemas.analytics_common import SearchOption

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
    average_activity_time: str | None = Field(
        description="Circular mean UTC time of dated ordinary messages, formatted HH:MM."
    )
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
    owner_opened_session_count: int = Field(
        description="Dated ordinary-message sessions opened by the owner."
    )
    measured_contact_reply_session_count: int = Field(
        description=(
            "Owner-opened sessions with a dated contact response within "
            "12 hours of the session's first message."
        )
    )
    message_interval_count: int = Field(
        description="Consecutive dated ordinary-message pairs within sessions."
    )
    average_response_seconds: float | None = Field(
        description=(
            "Mean time from the owner's first message to the contact's first "
            "response in each measured session; omitted unless at least five "
            "sessions are measured."
        )
    )
    longest_response_seconds: float | None = Field(
        description="Longest time from the owner's first message to the contact's first response in a measured session."
    )
    median_message_interval_seconds: float | None = Field(
        description="Median time between consecutive dated ordinary messages within sessions."
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


class ActivityPeriodCount(BaseModel):
    period: str
    count: int


class ChatInsightsStatistics(BaseModel):
    chat_id: int
    account_id: int
    platform: str
    source_account_label: str
    title: str | None
    chat_type: str
    ordinary_message_count: int
    average_activity_time: str | None = Field(
        description="Circular mean UTC time of dated ordinary messages, formatted HH:MM."
    )
    weekday_activity: list[ActivityPeriodCount] = Field(
        description="Dated ordinary-message counts by UTC weekday, Monday through Sunday."
    )
    month_activity: list[ActivityPeriodCount] = Field(
        description="Dated ordinary-message counts by UTC calendar month, January through December."
    )
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
    options: list[SearchOption] = Field(default_factory=list)
