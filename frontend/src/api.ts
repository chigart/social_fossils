import type { UploadPlatform } from "./platforms";

export type OverviewStatistics = {
  total_imported_accounts: number;
  total_chats: number;
  total_messages: number;
  total_ordinary_messages: number;
  total_service_messages: number;
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
  ordinary_messages: number;
  service_messages: number;
  earliest_message_timestamp: string | null;
  latest_message_timestamp: string | null;
  distinct_identified_senders: number;
};

export type ContactStatistics = {
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
  ordinary_messages_sent: number;
  service_events_attributed: number;
};

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
};

export type CommunicationTimelineMonth = {
  month: string;
  ordinary_message_count: number;
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

export type { UploadPlatform } from "./platforms";

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

async function getJson<T>(path: string): Promise<T> {
  let response: Response;

  try {
    response = await fetch(path);
  } catch {
    throw new Error("Unable to connect to the analytics API. Check that the backend is running.");
  }

  if (!response.ok) {
    throw new Error(`The analytics API returned an error (HTTP ${response.status}).`);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new Error("The analytics API returned an invalid response.");
  }
}

async function sendJson<T>(
  path: string,
  method: "POST" | "DELETE",
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      ...(body === undefined
        ? {}
        : {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    });
  } catch {
    throw new Error(
      "Unable to connect to identity links. Check that the backend is running.",
    );
  }

  let result: unknown;
  try {
    result = await response.json();
  } catch {
    throw new Error("The identity links API returned an invalid response.");
  }

  if (!response.ok) {
    const detail =
      typeof result === "object" &&
      result !== null &&
      "detail" in result &&
      typeof result.detail === "string"
        ? result.detail
        : `The identity links API returned an error (HTTP ${response.status}).`;
    throw new Error(detail);
  }
  return result as T;
}

export async function uploadFile(
  file: File,
  platform: UploadPlatform,
  onProgress?: (progress: UploadProgress) => void,
): Promise<UploadJob> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("platform", platform);

  return new Promise((resolve, reject) => {
    try {
      const request = new XMLHttpRequest();
      request.open("POST", "/api/uploads/upload");
      request.upload.onprogress = (event) => {
        onProgress?.({
          loadedBytes: event.loaded,
          ...(event.lengthComputable ? { totalBytes: event.total } : {}),
        });
      };
      request.onerror = () => {
        reject(
          new Error(
            "Unable to connect to the upload API. Check that the backend is running.",
          ),
        );
      };
      request.onload = () => {
        let body: unknown;
        try {
          body = JSON.parse(request.responseText) as unknown;
        } catch {
          reject(new Error("The upload API returned an invalid response."));
          return;
        }

        if (request.status < 200 || request.status >= 300) {
          const detail =
            typeof body === "object" &&
            body !== null &&
            "detail" in body &&
            typeof body.detail === "string"
              ? body.detail
              : `The upload API returned an error (HTTP ${request.status}).`;
          reject(new Error(detail));
          return;
        }

        resolve(body as UploadJob);
      };
      request.send(formData);
    } catch {
      reject(
        new Error(
          "Unable to connect to the upload API. Check that the backend is running.",
        ),
      );
    }
  });
}

export type UploadProgress = {
  loadedBytes: number;
  totalBytes?: number;
};

export async function retryUploadJob(jobId: number): Promise<UploadJob> {
  let response: Response;
  try {
    response = await fetch(`/api/uploads/jobs/${jobId}/retry`, {
      method: "POST",
    });
  } catch {
    throw new Error(
      "Unable to connect to the upload API. Check that the backend is running.",
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error("The upload API returned an invalid response.");
  }

  if (!response.ok) {
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : `The upload API returned an error (HTTP ${response.status}).`;
    throw new Error(detail);
  }

  return body as UploadJob;
}

export async function getUploadJobStatus(
  jobId: number,
): Promise<UploadJobStatus> {
  let response: Response;
  try {
    response = await fetch(`/api/uploads/jobs/${jobId}/status`);
  } catch {
    throw new Error(
      "Unable to connect to the upload API. Check that the backend is running.",
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error("The upload API returned an invalid response.");
  }

  if (!response.ok) {
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : `The upload API returned an error (HTTP ${response.status}).`;
    throw new Error(detail);
  }

  return body as UploadJobStatus;
}

export const getOverview = () =>
  getJson<OverviewStatistics>("/api/analytics/overview");

export const getChatInsights = () =>
  getJson<ChatInsightsResponse>("/api/analytics/chat-insights");

export const getChats = () => getJson<ChatStatistics[]>("/api/analytics/chats");

export const getContacts = () =>
  getJson<ContactStatistics[]>("/api/analytics/contacts");

export const getIdentityLinks = () =>
  getJson<IdentityLinksResponse>("/api/identity-links");

export const linkPlatformIdentities = (
  firstIdentityId: number,
  secondIdentityId: number,
) =>
  sendJson<IdentityLinkActionResponse>("/api/identity-links", "POST", {
    first_identity_id: firstIdentityId,
    second_identity_id: secondIdentityId,
  });

export const unlinkPlatformIdentity = (identityId: number) =>
  sendJson<IdentityLinkActionResponse>(
    `/api/identity-links/${identityId}`,
    "DELETE",
  );

export const getCommunicationBalance = () =>
  getJson<CommunicationBalanceStatistics>(
    "/api/analytics/communication-balance",
  );

export const getForgottenContacts = () =>
  getJson<ForgottenContactsStatistics>("/api/analytics/forgotten-contacts");

export const getCommunicationTimeline = (
  canonicalIdentityId?: number,
  chatId?: number,
) => {
  const parameters = [
    canonicalIdentityId === undefined
      ? null
      : `canonical_identity_id=${canonicalIdentityId}`,
    chatId === undefined ? null : `chat_id=${chatId}`,
  ].filter((parameter): parameter is string => parameter !== null);
  const query = parameters.length > 0 ? `?${parameters.join("&")}` : "";
  return getJson<CommunicationTimelineStatistics>(
    `/api/analytics/communication-timeline${query}`,
  );
};
