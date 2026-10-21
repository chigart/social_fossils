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

export const getOverview = () =>
  getJson<OverviewStatistics>("/api/analytics/overview");

export const getChats = () => getJson<ChatStatistics[]>("/api/analytics/chats");

export const getContacts = () =>
  getJson<ContactStatistics[]>("/api/analytics/contacts");

export const getCommunicationBalance = () =>
  getJson<CommunicationBalanceStatistics>(
    "/api/analytics/communication-balance",
  );
