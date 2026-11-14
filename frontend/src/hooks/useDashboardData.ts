import { useCallback, useRef, useState } from "react";
import {
  getChatInsights,
  getChats,
  getCommunicationBalance,
  getCommunicationTimeline,
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
  type ContactStatistics,
  type ContactSortBy,
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
  const chatPages = useRef(new Map<string, PaginatedItems<ChatStatistics>>());
  const contactPages = useRef(new Map<string, PaginatedItems<ContactStatistics>>());
  const balancePages = useRef(new Map<string, CommunicationBalanceStatistics>());
  const forgottenContactPages = useRef(
    new Map<string, ForgottenContactsStatistics>(),
  );
  const chatInsightPages = useRef(new Map<string, ChatInsightsResponse>());
  const chatInsightsRequestId = useRef(0);
  const chatRequestId = useRef(0);
  const activeChatScope = useRef<ChatScope | null>(null);
  const contactRequestId = useRef(0);
  const balanceRequestId = useRef(0);
  const forgottenContactRequestId = useRef(0);
  const activeForgottenScope = useRef<"private" | "group" | null>(null);
  const timelineRequestId = useRef(0);
  const loadedResources = useRef(new Set<string>());

  const loadOverview = useCallback(async (force = false) => {
    if (!force && loadedResources.current.has("overview")) return;
    loadedResources.current.add("overview");
    setOverview((current) => ({ ...current, error: null, loading: true }));
    try {
      setOverview({ data: await getOverview(), error: null, loading: false });
    } catch (error) {
      loadedResources.current.delete("overview");
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
    force = false,
    page = 1,
    sortBy: ChatSortBy = "total_messages",
    sortDirection: "asc" | "desc" = "desc",
    chatScope: ChatScope = "all",
  ) => {
    const requestId = ++chatRequestId.current;
    const cacheKey = `${chatScope}:${page}:${sortBy}:${sortDirection}`;
    const cachedPage = chatPages.current.get(cacheKey);
    const scopeChanged = activeChatScope.current !== chatScope;
    activeChatScope.current = chatScope;
    if (!force && cachedPage) {
      setChats({ data: cachedPage, error: null, loading: false });
      return;
    }
    setChats((current) => ({
      ...current,
      data: scopeChanged ? null : current.data,
      error: null,
      loading: true,
    }));
    try {
      const data = await getChats(
        page,
        DEFAULT_PAGE_SIZE,
        sortBy,
        sortDirection,
        chatScope,
      );
      chatPages.current.set(cacheKey, data);
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
    force = false,
    chatId?: number,
  ) => {
    const requestId = ++chatInsightsRequestId.current;
    const cacheKey = chatId === undefined ? "default" : `chat:${chatId}`;
    const cachedPage = chatInsightPages.current.get(cacheKey);
    if (!force && cachedPage) {
      setChatInsights({ data: cachedPage, error: null, loading: false });
      return;
    }
    setChatInsights((current) => ({ ...current, error: null, loading: true }));
    try {
      const data = await getChatInsights(chatId);
      chatInsightPages.current.set(cacheKey, data);
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
    force = false,
    page = 1,
    sortBy: ContactSortBy = "total_messages_sent",
    sortDirection: "asc" | "desc" = "desc",
  ) => {
    const requestId = ++contactRequestId.current;
    const cacheKey = `${page}:${sortBy}:${sortDirection}`;
    const cachedPage = contactPages.current.get(cacheKey);
    if (!force && cachedPage) {
      setContacts({ data: cachedPage, error: null, loading: false });
      return;
    }
    setContacts((current) => ({ ...current, error: null, loading: true }));
    try {
      const data = await getContacts(
        page,
        DEFAULT_PAGE_SIZE,
        sortBy,
        sortDirection,
      );
      contactPages.current.set(cacheKey, data);
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
    force = false,
    page = 1,
    sortBy: "text_volume" | "owner_share" | "recent_activity" = "text_volume",
    sortDirection: "asc" | "desc" = "desc",
    classification: CommunicationBalanceClassification | "all" = "all",
  ) => {
    const requestId = ++balanceRequestId.current;
    const cacheKey = `${page}:${sortBy}:${sortDirection}:${classification}`;
    const cachedPage = balancePages.current.get(cacheKey);
    if (!force && cachedPage) {
      setBalance({ data: cachedPage, error: null, loading: false });
      return;
    }
    setBalance((current) => ({ ...current, error: null, loading: true }));
    try {
      const data = await getCommunicationBalance(
        page,
        DEFAULT_PAGE_SIZE,
        sortBy,
        sortDirection,
        classification,
      );
      balancePages.current.set(cacheKey, data);
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
    force = false,
    page = 1,
    sortBy:
      | "ranking_score"
      | "display_name"
      | "days_since_last_communication" = "ranking_score",
    sortDirection: "asc" | "desc" = "desc",
    scope: "private" | "group" = "private",
  ) => {
    const requestId = ++forgottenContactRequestId.current;
    const cacheKey = `${scope}:${page}:${sortBy}:${sortDirection}`;
    const cachedPage = forgottenContactPages.current.get(cacheKey);
    const scopeChanged = activeForgottenScope.current !== scope;
    activeForgottenScope.current = scope;
    if (!force && cachedPage) {
      setForgottenContacts({
        data: cachedPage,
        error: null,
        loading: false,
      });
      return;
    }
    setForgottenContacts((current) => ({
      ...current,
      data: scopeChanged ? null : current.data,
      error: null,
      loading: true,
    }));
    try {
      const data = await getForgottenContacts(
        page,
        DEFAULT_PAGE_SIZE,
        sortBy,
        sortDirection,
        scope,
      );
      forgottenContactPages.current.set(cacheKey, data);
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

  const loadIdentityLinks = useCallback(async (force = false) => {
    if (!force && loadedResources.current.has("identityLinks")) return;
    loadedResources.current.add("identityLinks");
    setIdentityLinks((current) => ({ ...current, error: null, loading: true }));
    try {
      setIdentityLinks({
        data: await getIdentityLinks(),
        error: null,
        loading: false,
      });
    } catch (error) {
      loadedResources.current.delete("identityLinks");
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
  ) => {
    const requestId = ++timelineRequestId.current;
    setCommunicationTimeline(emptyResource);
    try {
      const data = await getCommunicationTimeline(
        canonicalIdentityId ?? undefined,
        chatId,
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

  return {
    overview,
    chats,
    chatInsights,
    contacts,
    balance,
    forgottenContacts,
    identityLinks,
    communicationTimeline,
    loadOverview,
    loadChats,
    loadChatInsights,
    loadContacts,
    loadBalance,
    loadForgottenContacts,
    loadIdentityLinks,
    loadCommunicationTimeline,
    createIdentityLink,
    removeIdentityLink,
  };
}
