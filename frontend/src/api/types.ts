import type { UploadPlatform } from "../utils/platforms";

export type OverviewStatistics = {
  total_imported_accounts: number;
  total_chats: number;
  total_messages: number;
  total_ordinary_messages: number;
  total_service_messages: number;
  imported_accounts: ImportedAccountStatistics[];
  earliest_message_timestamp: string | null;
  latest_message_timestamp: string | null;
};

export type PaginationMetadata = {
  page: number;
  page_size: number;
  total: number;
};

export type SearchOption = {
  value: string;
  label: string;
  platforms: string[];
  search_terms: string[];
  contact_id?: number;
};

export type PaginatedItems<T> = {
  items: T[];
  pagination: PaginationMetadata;
  options: SearchOption[];
};

export type ImportedAccountStatistics = {
  id: number;
  platform: string;
  name: string;
  username: string | null;
  platform_user_id: string | null;
  total_messages: number;
  total_text_length: number;
  total_contacts: number;
  earliest_message_timestamp: string | null;
  latest_message_timestamp: string | null;
};

export type WordFrequency = {
  word: string;
  count: number;
};

export type EmojiFrequency = {
  emoji: string;
  count: number;
};

export type ChatInsightSender = {
  sender_id: string | null;
  display_name: string;
  message_count: number;
  text_length: number;
  popular_words: WordFrequency[];
  popular_emojis: EmojiFrequency[];
};

export type ReactionReactor = {
  reactor_id: string;
  display_name: string;
  reaction_count: number;
  popular_emojis: EmojiFrequency[];
};

export type ReactionAuthorPair = {
  reactor_id: string;
  reactor_name: string;
  author_id: string;
  author_name: string;
  observed_reaction_count: number;
  messages_with_observed_reaction_count: number;
  author_message_count: number;
  observed_message_percentage: number;
};

export type MessageTypeCount = {
  category: string;
  count: number;
  with_text_count: number;
  senders: ConversationParticipantCount[];
};

export type ReplyTempoStatistics = {
  reply_reference_count: number;
  measured_reply_count: number;
  average_response_seconds: number | null;
  longest_response_seconds: number | null;
  median_response_seconds: number | null;
};

export type ConversationParticipantCount = {
  sender_id: string | null;
  display_name: string;
  count: number;
};

export type ConversationHandoffCount = {
  previous_closer_id: string;
  previous_closer_name: string;
  next_opener_id: string;
  next_opener_name: string;
  count: number;
};

export type ConversationActivityStatistics = {
  session_gap_hours: number;
  session_count: number;
  messages_without_timestamp_count: number;
  sender_transition_count: number;
  sender_switch_count: number;
  sender_switch_percentage: number;
  longest_turn_taking_streak: number;
  attributed_handoff_count: number;
  unattributed_handoff_count: number;
  opening_senders: ConversationParticipantCount[];
  closing_senders: ConversationParticipantCount[];
  handoffs: ConversationHandoffCount[];
};

export type ChatInsightsStatistics = {
  chat_id: number;
  account_id: number;
  platform: string;
  source_account_label: string;
  title: string | null;
  chat_type: string;
  ordinary_message_count: number;
  text_length: number;
  popular_words: WordFrequency[];
  popular_emojis: EmojiFrequency[];
  senders: ChatInsightSender[];
  reaction_count: number;
  reaction_emojis: EmojiFrequency[];
  reactors: ReactionReactor[];
  reactor_author_pairs: ReactionAuthorPair[];
  message_type_breakdown: MessageTypeCount[];
  reply_tempo: ReplyTempoStatistics;
  conversation_activity: ConversationActivityStatistics;
};

export type ChatInsightsResponse = {
  chats: ChatInsightsStatistics[];
  options?: SearchOption[];
};

export type ChatStatistics = {
  chat_id: number;
  account_id: number;
  platform: string;
  source_account_label: string;
  platform_chat_id: string;
  title: string | null;
  chat_type: string;
  total_messages: number;
  text_length: number;
  ordinary_messages: number;
  service_messages: number;
  average_response_seconds: number | null;
  earliest_message_timestamp: string | null;
  latest_message_timestamp: string | null;
  distinct_identified_senders: number;
};

export type ChatScope = "dm" | "group" | "all";

export type ChatSortBy =
  | "title"
  | "total_messages"
  | "text_length"
  | "average_response_seconds"
  | "distinct_identified_senders"
  | "earliest_message_timestamp"
  | "latest_message_timestamp";

export type FriendStatus = "Active" | "Close" | "exClose";

export type ContactStatistics = {
  friend_statuses: FriendStatus[];
  platforms: string[];
  account_id: number | null;
  identity_group_id: number | null;
  canonical_identity_id: number | null;
  source_account_ids: number[];
  source_account_labels: string[];
  source_accounts: { platform: string; label: string }[];
  source_contact_ids: number[];
  platform_user_ids: string[];
  display_name: string | null;
  total_messages_sent: number;
  personal_chat_messages_sent: number;
  group_chat_messages_sent: number;
  ordinary_messages_sent: number;
  service_events_attributed: number;
};

export type ContactSortBy =
  | "total_messages_sent"
  | "personal_chat_messages_sent"
  | "group_chat_messages_sent";

export type IdentityContactSource = {
  contact_id: number;
  account_id: number;
  account_label: string;
  platform: string;
  display_name: string | null;
  username: string | null;
};

export type PlatformIdentity = {
  identity_id: number;
  platform: string;
  platform_user_id: string;
  identity_group_id: number | null;
  is_owner: boolean;
  contacts: IdentityContactSource[];
};

export type UnidentifiedContact = {
  contact_id: number;
  account_id: number;
  account_label: string;
  platform: string;
  display_name: string | null;
  username: string | null;
};

export type IdentityLinkEvent = {
  id: number;
  group_id: number | null;
  identity_id: number;
  peer_identity_id: number | null;
  action: "linked" | "unlinked";
  source: string;
  occurred_at: string;
};

export type IdentityLinksResponse = {
  identities: PlatformIdentity[];
  contacts_without_identity: UnidentifiedContact[];
  events: IdentityLinkEvent[];
};

export type IdentityLinkActionResponse = {
  status: "linked" | "unlinked";
  identity_group_id: number | null;
};

export type CommunicationBalanceClassification =
  | "balanced"
  | "mostly_owner"
  | "mostly_contact"
  | "strongly_owner"
  | "strongly_contact"
  | "insufficient_data";

export type CommunicationBalanceContact = {
  account_id: number | null;
  contact_id: number;
  canonical_identity_id: number | null;
  identity_group_id: number | null;
  platforms: string[];
  source_account_ids: number[];
  source_account_labels: string[];
  source_contact_ids: number[];
  platform_user_ids: string[];
  display_name: string | null;
  owner_message_count: number;
  contact_message_count: number;
  total_message_count: number;
  excluded_unknown_direction_message_count: number;
  owner_text_length: number;
  contact_text_length: number;
  total_text_length: number;
  owner_text_share: number | null;
  contact_text_share: number | null;
  absolute_share_difference: number | null;
  owner_share_percentage: number | null;
  contact_share_percentage: number | null;
  classification: CommunicationBalanceClassification;
  first_message_at: string | null;
  last_message_at: string | null;
  distinct_active_days: number;
};

export type CommunicationBalanceSummary = {
  eligible_contacts: number;
  balanced_contacts: number;
  mostly_owner_contacts: number;
  mostly_contact_contacts: number;
  strongly_owner_contacts: number;
  strongly_contact_contacts: number;
  insufficient_data_contacts: number;
  owner_text_length: number;
  contact_text_length: number;
  total_text_length: number;
  owner_message_count: number;
  contact_message_count: number;
  total_message_count: number;
  excluded_unknown_direction_message_count: number;
};

export type CommunicationBalanceStatistics = {
  summary: CommunicationBalanceSummary;
  contacts: CommunicationBalanceContact[];
  pagination: PaginationMetadata;
  options: SearchOption[];
};

export type ForgottenContactClassification =
  | "insufficient_data"
  | "inactive"
  | "activity_declined"
  | "active";

export type ForgottenContactEvidenceStatus =
  | "reliable_baseline"
  | "insufficient_history"
  | "insufficient_baseline"
  | "ambiguous_direction";

export type ForgottenContactMonthlyActivity = {
  month: string;
  owner_message_count: number;
  contact_message_count: number;
  total_message_count: number;
};

export type ForgottenContact = {
  account_id: number | null;
  contact_id: number;
  canonical_identity_id: number | null;
  identity_group_id: number | null;
  platforms: string[];
  source_account_ids: number[];
  source_account_labels: string[];
  source_contact_ids: number[];
  platform_user_ids: string[];
  display_name: string | null;
  interaction_chat_count: number;
  first_message_at: string | null;
  last_message_at: string | null;
  days_since_last_communication: number | null;
  owner_message_count: number;
  contact_message_count: number;
  total_message_count: number;
  excluded_ambiguous_message_count: number;
  owner_text_length: number;
  contact_text_length: number;
  total_text_length: number;
  distinct_active_days: number;
  historical_message_count: number;
  historical_active_days: number;
  historical_active_month_count: number;
  historical_activity_by_month: ForgottenContactMonthlyActivity[];
  recent_activity_by_month: ForgottenContactMonthlyActivity[];
  recent_owner_message_count: number;
  recent_contact_message_count: number;
  recent_message_count: number;
  historical_monthly_baseline: number | null;
  recent_monthly_activity: number;
  activity_decline_percentage: number | null;
  classification: ForgottenContactClassification;
  evidence_status: ForgottenContactEvidenceStatus;
  ranking_score: number | null;
};

export type ForgottenContactsSummary = {
  scope: "combined_owner";
  source_account_count: number;
  eligible_contacts: number;
  meaningful_historical_contacts: number;
  currently_inactive_contacts: number;
  declining_activity_contacts: number;
  insufficient_data_contacts: number;
};

export type ForgottenContactsStatistics = {
  summary: ForgottenContactsSummary;
  contacts: ForgottenContact[];
  pagination: PaginationMetadata;
  options: SearchOption[];
};

export type CommunicationTimelineMonth = {
  month: string;
  ordinary_message_count: number;
  text_length: number;
  owner_text_length: number;
  owner_message_count: number;
  contact_message_count: number;
  unknown_direction_message_count: number;
  active_days: number;
  owner_active_days: number;
  contact_active_days: number;
  unknown_direction_active_days: number;
};

export type CommunicationTimelineSummary = {
  scope: "owner" | "contact" | "chat";
  chat_id: number | null;
  canonical_identity_id: number | null;
  identity_group_id: number | null;
  source_account_count: number;
  source_account_ids: number[];
  source_account_labels: string[];
  source_contact_ids: number[];
  ordinary_message_count: number;
  dated_ordinary_message_count: number;
  undated_ordinary_message_count: number;
  owner_message_count: number;
  contact_message_count: number;
  unknown_direction_message_count: number;
  undated_owner_message_count: number;
  undated_contact_message_count: number;
  undated_unknown_direction_message_count: number;
};

export type CommunicationTimelineStatistics = {
  summary: CommunicationTimelineSummary;
  months: CommunicationTimelineMonth[];
};

export type CloseFriendsTimelineYear = {
  year: number;
  close_friend_count: number;
};

export type CloseFriendsTimelineStatistics = {
  years: CloseFriendsTimelineYear[];
};

export type { UploadPlatform } from "../utils/platforms";

export type UploadJob = {
  id: number;
  filename: string;
  platform: UploadPlatform;
  status: "pending" | "processing" | "completed" | "failed";
  source_account_id: number | null;
  import_session_id: number | null;
  airflow_dag_run_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  warning_message?: string | null;
  created_at: string;
};

export type AirflowTaskStatus = {
  task_id: string;
  state: string | null;
  start_date: string | null;
  end_date: string | null;
};

export type UploadJobStatus = UploadJob & {
  airflow_run_details?: {
    state: string | null;
    start_date: string | null;
    end_date: string | null;
  };
  airflow_tasks?: AirflowTaskStatus[];
  airflow_error?: string;
};

export type AIMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AIProvider = "ollama" | "openai-compatible";

export type AIChatRequest = {
  provider: AIProvider;
  model: string;
  messages: AIMessage[];
  api_key?: string;
  base_url?: string;
};

export type AIChatResponse = {
  answer: string;
};

export type AIModelsResponse = {
  models: string[];
};
