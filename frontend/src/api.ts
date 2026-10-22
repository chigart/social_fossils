export type OverviewStatistics = {
  total_imported_accounts: number;
  total_chats: number;
  total_messages: number;
  total_ordinary_messages: number;
  total_service_messages: number;
  earliest_message_timestamp: string | null;
  latest_message_timestamp: string | null;
};

export type ChatStatistics = {
  chat_id: number;
  account_id: number;
  source_account_label: string;
  telegram_chat_id: string;
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
  account_id: number | null;
  contact_id: number | null;
  canonical_identity_id: number | null;
  source_account_ids: number[];
  source_account_labels: string[];
  source_contact_ids: number[];
  telegram_user_id: string | null;
  display_name: string | null;
  total_messages_sent: number;
  ordinary_messages_sent: number;
  service_events_attributed: number;
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
  source_account_ids: number[];
  source_account_labels: string[];
  source_contact_ids: number[];
  telegram_user_id: string;
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
  source_account_ids: number[];
  source_account_labels: string[];
  source_contact_ids: number[];
  telegram_user_id: string;
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
  scope: "owner" | "contact";
  canonical_identity_id: number | null;
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

export type UploadJob = {
  id: number;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  source_account_id: number | null;
  import_session_id: number | null;
  airflow_dag_run_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
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

export async function uploadFile(file: File): Promise<UploadJob> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch("/api/uploads/upload", {
      method: "POST",
      body: formData,
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

export const getOverview = () =>
  getJson<OverviewStatistics>("/api/analytics/overview");

export const getChats = () => getJson<ChatStatistics[]>("/api/analytics/chats");

export const getContacts = () =>
  getJson<ContactStatistics[]>("/api/analytics/contacts");

export const getCommunicationBalance = () =>
  getJson<CommunicationBalanceStatistics>(
    "/api/analytics/communication-balance",
  );

export const getForgottenContacts = () =>
  getJson<ForgottenContactsStatistics>("/api/analytics/forgotten-contacts");

export const getCommunicationTimeline = (canonicalIdentityId?: number) =>
  getJson<CommunicationTimelineStatistics>(
    canonicalIdentityId === undefined
      ? "/api/analytics/communication-timeline"
      : `/api/analytics/communication-timeline?canonical_identity_id=${canonicalIdentityId}`,
  );
