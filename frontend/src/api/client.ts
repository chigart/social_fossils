import { DEFAULT_PAGE_SIZE } from "../constants";
import type {
  ChatInsightsResponse,
  ChatSortBy,
  ChatScope,
  ChatStatistics,
  CloseFriendsTimelineStatistics,
  CommunicationBalanceClassification,
  CommunicationBalanceStatistics,
  CommunicationTimelineStatistics,
  ContactStatistics,
  ContactSortBy,
  FriendStatus,
  ForgottenContact,
  ForgottenContactsStatistics,
  IdentityLinkActionResponse,
  IdentityLinksResponse,
  OverviewStatistics,
  PaginatedItems,
  UploadJob,
  UploadJobStatus,
  UploadPlatform,
} from "./types";

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

export const getChatInsights = (chatId?: number) => {
  const query =
    chatId === undefined ? "" : `?chat_id=${encodeURIComponent(chatId)}`;
  return getJson<ChatInsightsResponse>(
    `/api/analytics/chat-insights${query}`,
  );
};

function pageQuery(
  page: number,
  pageSize: number,
  filters: Record<string, string> = {},
): string {
  const parameters = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    ...filters,
  });
  return `?${parameters.toString()}`;
}

export const getChats = (
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE,
  sortBy: ChatSortBy = "total_messages",
  sortDirection: "asc" | "desc" = "desc",
  chatScope: ChatScope = "all",
  platform?: string,
) =>
  getJson<PaginatedItems<ChatStatistics>>(
    `/api/analytics/chats${pageQuery(page, pageSize, {
      sort_by: sortBy,
      sort_direction: sortDirection,
      ...(chatScope === "all" ? {} : { chat_scope: chatScope }),
      ...(platform ? { platform } : {}),
    })}`,
  );

export const getContacts = (
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE,
  sortBy: ContactSortBy = "total_messages_sent",
  sortDirection: "asc" | "desc" = "desc",
  platform?: string,
  friendStatus?: FriendStatus,
) =>
  getJson<PaginatedItems<ContactStatistics>>(
    `/api/analytics/contacts${pageQuery(page, pageSize, {
      sort_by: sortBy,
      sort_direction: sortDirection,
      ...(platform ? { platform } : {}),
      ...(friendStatus ? { friend_status: friendStatus } : {}),
    })}`,
  );

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

export const getCommunicationBalance = (
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE,
  sortBy: "text_volume" | "owner_share" | "recent_activity" = "text_volume",
  sortDirection: "asc" | "desc" = "desc",
  classification?: CommunicationBalanceClassification | "all",
  platform?: string,
) =>
  getJson<CommunicationBalanceStatistics>(
    `/api/analytics/communication-balance${pageQuery(page, pageSize, {
      sort_by: sortBy,
      sort_direction: sortDirection,
      ...(classification && classification !== "all"
        ? { classification }
        : {}),
      ...(platform ? { platform } : {}),
    })}`,
  );

export const getForgottenContacts = (
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE,
  sortBy:
    | "ranking_score"
    | "display_name"
    | "days_since_last_communication" = "ranking_score",
  sortDirection: "asc" | "desc" = "desc",
  scope: "private" | "group" = "private",
  platform?: string,
) =>
  getJson<ForgottenContactsStatistics>(
    `/api/analytics/forgotten-contacts${pageQuery(page, pageSize, {
      sort_by: sortBy,
      sort_direction: sortDirection,
      scope,
      ...(platform ? { platform } : {}),
    })}`,
  );

export const getGroupInteraction = (contactId: number) =>
  getJson<ForgottenContact>(
    `/api/analytics/group-interactions/${encodeURIComponent(contactId)}`,
  );

export const getCommunicationTimeline = (
  canonicalIdentityId?: number,
  chatId?: number,
  senderId?: string | null,
  accountId?: number,
) => {
  const parameters = [
    canonicalIdentityId === undefined
      ? null
      : `canonical_identity_id=${canonicalIdentityId}`,
    chatId === undefined ? null : `chat_id=${chatId}`,
    senderId == null ? null : `sender_id=${encodeURIComponent(senderId)}`,
    accountId === undefined ? null : `account_id=${accountId}`,
  ].filter((parameter): parameter is string => parameter !== null);
  const query = parameters.length > 0 ? `?${parameters.join("&")}` : "";
  return getJson<CommunicationTimelineStatistics>(
    `/api/analytics/communication-timeline${query}`,
  );
};

export const getCloseFriendsTimeline = () =>
  getJson<CloseFriendsTimelineStatistics>(
    "/api/analytics/close-friends-timeline",
  );
