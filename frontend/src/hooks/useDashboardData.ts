import { useEffect, useRef, useState } from "react";
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
  const [selectedTimelineContactId, setSelectedTimelineContactId] =
    useState<number | null>(null);
  const timelineRequestId = useRef(0);

  const loadOverview = async () => {
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
  };

  const loadChats = async () => {
    setChats((current) => ({ ...current, error: null, loading: true }));
    try {
      setChats({ data: await getChats(), error: null, loading: false });
    } catch (error) {
      setChats((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load chat statistics.",
        loading: false,
      }));
    }
  };

  const loadChatInsights = async () => {
    setChatInsights((current) => ({ ...current, error: null, loading: true }));
    try {
      setChatInsights({
        data: await getChatInsights(),
        error: null,
        loading: false,
      });
    } catch (error) {
      setChatInsights((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load chat insights.",
        loading: false,
      }));
    }
  };

  const loadContacts = async () => {
    setContacts((current) => ({ ...current, error: null, loading: true }));
    try {
      setContacts({ data: await getContacts(), error: null, loading: false });
    } catch (error) {
      setContacts((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load contact statistics.",
        loading: false,
      }));
    }
  };

  const loadBalance = async () => {
    setBalance((current) => ({ ...current, error: null, loading: true }));
    try {
      setBalance({
        data: await getCommunicationBalance(),
        error: null,
        loading: false,
      });
    } catch (error) {
      setBalance((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load communication balance statistics.",
        loading: false,
      }));
    }
  };

  const loadForgottenContacts = async () => {
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
      setForgottenContacts((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load forgotten contacts.",
        loading: false,
      }));
    }
  };

  const loadIdentityLinks = async () => {
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
  };

  const createIdentityLink = async (
    firstIdentityId: number,
    secondIdentityId: number,
  ) => {
    await linkPlatformIdentities(firstIdentityId, secondIdentityId);
    await loadIdentityLinks();
  };

  const removeIdentityLink = async (identityId: number) => {
    await unlinkPlatformIdentity(identityId);
    await loadIdentityLinks();
  };

  const loadCommunicationTimeline = async (
    canonicalIdentityId = selectedTimelineContactId,
  ) => {
    const requestId = ++timelineRequestId.current;
    setCommunicationTimeline((current) => ({
      ...current,
      error: null,
      loading: true,
    }));
    try {
      const data = await getCommunicationTimeline(
        canonicalIdentityId ?? undefined,
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
  };

  useEffect(() => {
    void loadOverview();
    void loadChats();
    void loadChatInsights();
    void loadContacts();
    void loadBalance();
    void loadForgottenContacts();
    void loadIdentityLinks();
  }, []);

  useEffect(() => {
    void loadCommunicationTimeline(selectedTimelineContactId);
  }, [selectedTimelineContactId]);

  return {
    overview,
    chats,
    chatInsights,
    contacts,
    balance,
    forgottenContacts,
    identityLinks,
    communicationTimeline,
    selectedTimelineContactId,
    setSelectedTimelineContactId,
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
