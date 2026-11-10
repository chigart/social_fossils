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
  type ChatInsightsResponse,
  type ChatStatistics,
  type CommunicationBalanceStatistics,
  type CommunicationTimelineStatistics,
  type ContactStatistics,
  type ForgottenContactsStatistics,
  type IdentityLinksResponse,
  type OverviewStatistics,
} from "../api";
import type { Resource } from "../types";

function emptyResource<T>(): Resource<T> {
  return { data: null, error: null, loading: true };
}

export function useDashboardData() {
  const [overview, setOverview] =
    useState<Resource<OverviewStatistics>>(emptyResource);
  const [chats, setChats] = useState<Resource<ChatStatistics[]>>(emptyResource);
  const [chatInsights, setChatInsights] =
    useState<Resource<ChatInsightsResponse>>(emptyResource);
  const [contacts, setContacts] =
    useState<Resource<ContactStatistics[]>>(emptyResource);
  const [balance, setBalance] =
    useState<Resource<CommunicationBalanceStatistics>>(emptyResource);
  const [forgottenContacts, setForgottenContacts] =
    useState<Resource<ForgottenContactsStatistics>>(emptyResource);
  const [identityLinks, setIdentityLinks] =
    useState<Resource<IdentityLinksResponse>>(emptyResource);
  const [communicationTimeline, setCommunicationTimeline] =
    useState<Resource<CommunicationTimelineStatistics>>(emptyResource);
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

  const loadChats = useCallback(async (force = false) => {
    if (!force && loadedResources.current.has("chats")) return;
    loadedResources.current.add("chats");
    setChats((current) => ({ ...current, error: null, loading: true }));
    try {
      setChats({ data: await getChats(), error: null, loading: false });
    } catch (error) {
      loadedResources.current.delete("chats");
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

  const loadChatInsights = useCallback(async (force = false) => {
    if (!force && loadedResources.current.has("chatInsights")) return;
    loadedResources.current.add("chatInsights");
    setChatInsights((current) => ({ ...current, error: null, loading: true }));
    try {
      setChatInsights({
        data: await getChatInsights(),
        error: null,
        loading: false,
      });
    } catch (error) {
      loadedResources.current.delete("chatInsights");
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

  const loadContacts = useCallback(async (force = false) => {
    if (!force && loadedResources.current.has("contacts")) return;
    loadedResources.current.add("contacts");
    setContacts((current) => ({ ...current, error: null, loading: true }));
    try {
      setContacts({ data: await getContacts(), error: null, loading: false });
    } catch (error) {
      loadedResources.current.delete("contacts");
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

  const loadBalance = useCallback(async (force = false) => {
    if (!force && loadedResources.current.has("balance")) return;
    loadedResources.current.add("balance");
    setBalance((current) => ({ ...current, error: null, loading: true }));
    try {
      setBalance({
        data: await getCommunicationBalance(),
        error: null,
        loading: false,
      });
    } catch (error) {
      loadedResources.current.delete("balance");
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

  const loadForgottenContacts = useCallback(async (force = false) => {
    if (!force && loadedResources.current.has("forgottenContacts")) return;
    loadedResources.current.add("forgottenContacts");
    setForgottenContacts((current) => ({
      ...current,
      error: null,
      loading: true,
    }));
    try {
      setForgottenContacts({
        data: await getForgottenContacts(),
        error: null,
        loading: false,
      });
    } catch (error) {
      loadedResources.current.delete("forgottenContacts");
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
