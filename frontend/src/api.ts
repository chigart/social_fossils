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
  account_id: number;
  contact_id: number | null;
  telegram_user_id: string | null;
  display_name: string | null;
  total_messages_sent: number;
  ordinary_messages_sent: number;
  service_events_attributed: number;
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
