import { useCallback, useRef, useState } from "react";
import {
  getChatInsights,
  getChats,
  getCommunicationBalance,
  getCommunicationTimeline,
  getCloseFriendsTimeline,
  getOwnerReplyTimeline,
  getContacts,
  getForgottenContacts,
  getIdentityLinks,
  getOverview,
  linkPlatformIdentities,
  unlinkPlatformIdentity,
  type ChatScope,
  type ChatSortBy,
  type ChatInsightsResponse,
  type ChatStatistics,
  type CommunicationBalanceClassification,
  type CommunicationBalanceStatistics,
  type CommunicationTimelineStatistics,
  type CloseFriendsTimelineStatistics,
  type OwnerReplyTimelineStatistics,
  type ContactStatistics,
  type ContactSortBy,
  type FriendStatus,
  type ForgottenContactsStatistics,
  type IdentityLinksResponse,
  type OverviewStatistics,
  type PaginatedItems,
} from "../api";
import { DEFAULT_PAGE_SIZE } from "../constants";
import type { Resource } from "../types";

function emptyResource<T>(): Resource<T> {
  return { data: null, error: null, loading: true };
}

export function useDashboardData() {
  const [overview, setOverview] =
    useState<Resource<OverviewStatistics>>(emptyResource);
  const [chats, setChats] =
    useState<Resource<PaginatedItems<ChatStatistics>>>(emptyResource);
  const [chatInsights, setChatInsights] =
    useState<Resource<ChatInsightsResponse>>(emptyResource);
  const [contacts, setContacts] =
    useState<Resource<PaginatedItems<ContactStatistics>>>(emptyResource);
  const [balance, setBalance] =
    useState<Resource<CommunicationBalanceStatistics>>(emptyResource);
  const [forgottenContacts, setForgottenContacts] =
    useState<Resource<ForgottenContactsStatistics>>(emptyResource);
  const [identityLinks, setIdentityLinks] =
    useState<Resource<IdentityLinksResponse>>(emptyResource);
  const [communicationTimeline, setCommunicationTimeline] =
    useState<Resource<CommunicationTimelineStatistics>>(emptyResource);
  const [closeFriendsTimeline, setCloseFriendsTimeline] =
    useState<Resource<CloseFriendsTimelineStatistics>>(emptyResource);
  const [ownerReplyTimeline, setOwnerReplyTimeline] =
    useState<Resource<OwnerReplyTimelineStatistics>>(emptyResource);
  const chatInsightsRequestId = useRef(0);
  const chatRequestId = useRef(0);
  const activeChatScope = useRef<ChatScope | null>(null);
  const contactRequestId = useRef(0);
  const balanceRequestId = useRef(0);
  const forgottenContactRequestId = useRef(0);
  const activeForgottenScope = useRef<"private" | "group" | null>(null);
  const timelineRequestId = useRef(0);
  const closeFriendsTimelineRequestId = useRef(0);
  const ownerReplyTimelineRequestId = useRef(0);

  const loadOverview = useCallback(async (_force = false) => {
    setOverview((current) => ({ ...current, error: null, loading: true }));
    try {
      setOverview({ data: await getOverview(), error: null, loading: false });
    } catch (error) {
      setOverview((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load overview statistics.",
        loading: false,
      }));
    }
  }, []);

  const loadChats = useCallback(async (
    _force = false,
    page = 1,
    sortBy: ChatSortBy = "total_messages",
    sortDirection: "asc" | "desc" = "desc",
    chatScope: ChatScope = "all",
    platform = "",
  ) => {
    const requestId = ++chatRequestId.current;
    const scopeChanged = activeChatScope.current !== chatScope;
    activeChatScope.current = chatScope;
    setChats((current) => ({
      ...current,
      data: scopeChanged ? null : current.data,
      error: null,
      loading: true,
    }));
    try {
      const data = platform
        ? await getChats(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            chatScope,
            platform,
          )
        : await getChats(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            chatScope,
          );
      if (requestId !== chatRequestId.current) return;
      setChats({
        data,
        error: null,
        loading: false,
      });
    } catch (error) {
      if (requestId !== chatRequestId.current) return;
      setChats((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load chat statistics.",
        loading: false,
      }));
    }
  }, []);

  const loadChatInsights = useCallback(async (
    _force = false,
    chatId?: number,
  ) => {
    const requestId = ++chatInsightsRequestId.current;
    setChatInsights((current) => ({ ...current, error: null, loading: true }));
    try {
      const data = await getChatInsights(chatId);
      if (requestId !== chatInsightsRequestId.current) return;
      setChatInsights({
        data,
        error: null,
        loading: false,
      });
    } catch (error) {
      if (requestId !== chatInsightsRequestId.current) return;
      setChatInsights((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load chat insights.",
        loading: false,
      }));
    }
  }, []);

  const loadContacts = useCallback(async (
    _force = false,
    page = 1,
    sortBy: ContactSortBy = "total_messages_sent",
    sortDirection: "asc" | "desc" = "desc",
    platform = "",
    friendStatus: FriendStatus | "" = "",
  ) => {
    const requestId = ++contactRequestId.current;
    setContacts((current) => ({ ...current, error: null, loading: true }));
    try {
      const data =
        platform && friendStatus
          ? await getContacts(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            platform,
            friendStatus,
          )
          : platform
            ? await getContacts(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            platform,
          )
            : friendStatus
              ? await getContacts(
                  page,
                  DEFAULT_PAGE_SIZE,
                  sortBy,
                  sortDirection,
                  undefined,
                  friendStatus,
                )
              : await getContacts(
                  page,
                  DEFAULT_PAGE_SIZE,
                  sortBy,
                  sortDirection,
                );
      if (requestId !== contactRequestId.current) return;
      setContacts({
        data,
        error: null,
        loading: false,
      });
    } catch (error) {
      if (requestId !== contactRequestId.current) return;
      setContacts((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load contact statistics.",
        loading: false,
      }));
    }
  }, []);

  const loadBalance = useCallback(async (
    _force = false,
    page = 1,
    sortBy: "text_volume" | "owner_share" | "recent_activity" = "text_volume",
    sortDirection: "asc" | "desc" = "desc",
    classification: CommunicationBalanceClassification | "all" = "all",
    platform = "",
  ) => {
    const requestId = ++balanceRequestId.current;
    setBalance((current) => ({ ...current, error: null, loading: true }));
    try {
      const data = platform
        ? await getCommunicationBalance(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            classification,
            platform,
          )
        : await getCommunicationBalance(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            classification,
          );
      if (requestId !== balanceRequestId.current) return;
      setBalance({
        data,
        error: null,
        loading: false,
      });
    } catch (error) {
      if (requestId !== balanceRequestId.current) return;
      setBalance((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load communication balance statistics.",
        loading: false,
      }));
    }
  }, []);

  const loadForgottenContacts = useCallback(async (
    _force = false,
    page = 1,
    sortBy:
      | "ranking_score"
      | "display_name"
      | "days_since_last_communication" = "ranking_score",
    sortDirection: "asc" | "desc" = "desc",
    scope: "private" | "group" = "private",
    platform = "",
  ) => {
    const requestId = ++forgottenContactRequestId.current;
    const scopeChanged = activeForgottenScope.current !== scope;
    activeForgottenScope.current = scope;
    setForgottenContacts((current) => ({
      ...current,
      data: scopeChanged ? null : current.data,
      error: null,
      loading: true,
    }));
    try {
      const data = platform
        ? await getForgottenContacts(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            scope,
            platform,
          )
        : await getForgottenContacts(
            page,
            DEFAULT_PAGE_SIZE,
            sortBy,
            sortDirection,
            scope,
          );
      if (requestId !== forgottenContactRequestId.current) return;
      setForgottenContacts({
        data,
        error: null,
        loading: false,
      });
    } catch (error) {
      if (requestId !== forgottenContactRequestId.current) return;
      setForgottenContacts((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load forgotten contacts.",
        loading: false,
      }));
    }
  }, []);

  const loadIdentityLinks = useCallback(async (_force = false) => {
    setIdentityLinks((current) => ({ ...current, error: null, loading: true }));
    try {
      setIdentityLinks({
        data: await getIdentityLinks(),
        error: null,
        loading: false,
      });
    } catch (error) {
      setIdentityLinks((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load platform identities.",
        loading: false,
      }));
    }
  }, []);

  const createIdentityLink = async (
    firstIdentityId: number,
    secondIdentityId: number,
  ) => {
    await linkPlatformIdentities(firstIdentityId, secondIdentityId);
    await loadIdentityLinks(true);
  };

  const removeIdentityLink = async (identityId: number) => {
    await unlinkPlatformIdentity(identityId);
    await loadIdentityLinks(true);
  };

  const loadCommunicationTimeline = useCallback(async (
    canonicalIdentityId?: number,
    chatId?: number,
    senderId?: string | null,
    accountId?: number,
  ) => {
    const requestId = ++timelineRequestId.current;
    setCommunicationTimeline(emptyResource);
    try {
      const data = accountId === undefined
        ? await getCommunicationTimeline(
            canonicalIdentityId ?? undefined,
            chatId,
            senderId,
          )
        : await getCommunicationTimeline(
            canonicalIdentityId ?? undefined,
            chatId,
            senderId,
            accountId,
          );
      if (requestId === timelineRequestId.current) {
        setCommunicationTimeline({ data, error: null, loading: false });
      }
    } catch (error) {
      if (requestId === timelineRequestId.current) {
        setCommunicationTimeline((current) => ({
          ...current,
          error:
            error instanceof Error
              ? error.message
              : "Unable to load communication timeline.",
          loading: false,
        }));
      }
    }
  }, []);

  const loadCloseFriendsTimeline = useCallback(async () => {
    const requestId = ++closeFriendsTimelineRequestId.current;
    setCloseFriendsTimeline((current) => ({
      ...current,
      error: null,
      loading: true,
    }));
    try {
      const data = await getCloseFriendsTimeline();
      if (requestId === closeFriendsTimelineRequestId.current) {
        setCloseFriendsTimeline({ data, error: null, loading: false });
      }
    } catch (error) {
      if (requestId === closeFriendsTimelineRequestId.current) {
        setCloseFriendsTimeline((current) => ({
          ...current,
          error:
            error instanceof Error
              ? error.message
              : "Unable to load close-friends timeline.",
          loading: false,
        }));
      }
    }
  }, []);

  const loadOwnerReplyTimeline = useCallback(async () => {
    const requestId = ++ownerReplyTimelineRequestId.current;
    setOwnerReplyTimeline((current) => ({
      ...current,
      error: null,
      loading: true,
    }));
    try {
      const data = await getOwnerReplyTimeline();
      if (requestId === ownerReplyTimelineRequestId.current) {
        setOwnerReplyTimeline({ data, error: null, loading: false });
      }
    } catch (error) {
      if (requestId === ownerReplyTimelineRequestId.current) {
        setOwnerReplyTimeline((current) => ({
          ...current,
          error:
            error instanceof Error
              ? error.message
              : "Unable to load owner reply timeline.",
          loading: false,
        }));
      }
    }
  }, []);

  return {
    overview,
    chats,
    chatInsights,
    contacts,
    balance,
    forgottenContacts,
    identityLinks,
    communicationTimeline,
    closeFriendsTimeline,
    ownerReplyTimeline,
    loadOverview,
    loadChats,
    loadChatInsights,
    loadContacts,
    loadBalance,
    loadForgottenContacts,
    loadIdentityLinks,
    loadCommunicationTimeline,
    loadCloseFriendsTimeline,
    loadOwnerReplyTimeline,
    createIdentityLink,
    removeIdentityLink,
  };
}
