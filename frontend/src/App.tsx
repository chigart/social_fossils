import { useEffect, useRef, useState } from "react";
import {
  getChats,
  getChatInsights,
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
  type CommunicationBalanceClassification,
  type CommunicationBalanceStatistics,
  type CommunicationTimelineStatistics,
  type ContactStatistics,
  type ForgottenContactsStatistics,
  type IdentityLinksResponse,
  type OverviewStatistics,
} from "./api";
import { ChatsView } from "./components/ChatsView";
import { ChatInsightsView } from "./components/ChatInsightsView";
import {
  CommunicationBalanceView,
  sortCommunicationBalanceContacts,
  type BalanceSortKey,
} from "./components/CommunicationBalanceView";
import { ContactsView } from "./components/ContactsView";
import { DashboardHeader } from "./components/DashboardHeader";
import { DashboardIntro } from "./components/DashboardIntro";
import { CommunicationTimelineView } from "./components/CommunicationTimelineView";
import { ForgottenContactsView } from "./components/ForgottenContactsView";
import { IdentityLinksView } from "./components/IdentityLinksView";
import { OverviewView } from "./components/OverviewView";
import { UploadView } from "./components/UploadView";
import {
  dashboardTabFromHash,
  type DashboardTab,
} from "./components/dashboardTabs";
import type { Resource, SortDirection } from "./types";

function emptyResource<T>(): Resource<T> {
  return { data: null, error: null, loading: true };
}

export default function App() {
  const [overview, setOverview] =
    useState<Resource<OverviewStatistics>>(emptyResource);
  const [chats, setChats] = useState<Resource<ChatStatistics[]>>(emptyResource);
  const [chatInsights, setChatInsights] =
    useState<Resource<ChatInsightsResponse>>(emptyResource);
  const [selectedInsightsChatId, setSelectedInsightsChatId] =
    useState<number | null>(null);
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
  const [selectedTab, setSelectedTab] = useState<DashboardTab>(() =>
    dashboardTabFromHash(window.location.hash),
  );
  const [chatSearch, setChatSearch] = useState("");
  const [contactSearch, setContactSearch] = useState("");
  const [balanceSearch, setBalanceSearch] = useState("");
  const [forgottenSearch, setForgottenSearch] = useState("");
  const [balanceClassification, setBalanceClassification] = useState<
    CommunicationBalanceClassification | "all"
  >("all");
  const [forgottenSortKey, setForgottenSortKey] = useState<
    "ranking_score" | "display_name" | "days_since_last_communication"
  >("ranking_score");
  const [forgottenSortDirection, setForgottenSortDirection] =
    useState<SortDirection>("desc");
  const [balanceSortKey, setBalanceSortKey] =
    useState<BalanceSortKey>("text_volume");
  const [balanceSortDirection, setBalanceSortDirection] =
    useState<SortDirection>("desc");
  const [chatSort, setChatSort] = useState<{
    key: "title" | "total_messages";
    direction: SortDirection;
  }>({ key: "total_messages", direction: "desc" });
  const [contactSortDirection, setContactSortDirection] =
    useState<SortDirection>("desc");

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
    setForgottenContacts((current) => ({ ...current, error: null, loading: true }));
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

  useEffect(() => {
    const syncSelectedTab = () =>
      setSelectedTab(dashboardTabFromHash(window.location.hash));
    window.addEventListener("hashchange", syncSelectedTab);
    window.addEventListener("popstate", syncSelectedTab);
    return () => {
      window.removeEventListener("hashchange", syncSelectedTab);
      window.removeEventListener("popstate", syncSelectedTab);
    };
  }, []);

  const changeChatSort = (key: "title" | "total_messages") => {
    setChatSort((current) => ({
      key,
      direction:
        current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  };

  const visibleChats = (chats.data ?? [])
    .filter((chat) =>
      (chat.title ?? "Untitled chat")
        .toLocaleLowerCase()
        .includes(chatSearch.trim().toLocaleLowerCase()),
    )
    .sort((left, right) => {
      const comparison =
        chatSort.key === "title"
          ? (left.title ?? "").localeCompare(right.title ?? "")
          : left.total_messages - right.total_messages;
      return chatSort.direction === "asc" ? comparison : -comparison;
    });

  const visibleContacts = (contacts.data ?? [])
    .filter((contact) =>
      (contact.display_name ?? "")
        .toLocaleLowerCase()
        .includes(contactSearch.trim().toLocaleLowerCase()),
    )
    .sort(
      (left, right) =>
        (contactSortDirection === "asc" ? 1 : -1) *
        (left.total_messages_sent - right.total_messages_sent),
    );

  const visibleBalanceContacts = sortCommunicationBalanceContacts(
    (balance.data?.contacts ?? [])
      .filter((contact) =>
        (contact.display_name ?? "")
          .toLocaleLowerCase()
          .includes(balanceSearch.trim().toLocaleLowerCase()),
      )
      .filter(
        (contact) =>
          balanceClassification === "all" ||
          contact.classification === balanceClassification,
      ),
    balanceSortKey,
    balanceSortDirection,
  );

  const visibleForgottenContacts = (forgottenContacts.data?.contacts ?? [])
    .filter((contact) =>
      (contact.display_name ?? "")
        .toLocaleLowerCase()
        .includes(forgottenSearch.trim().toLocaleLowerCase()),
    )
    .sort((left, right) => {
      const direction = forgottenSortDirection === "asc" ? 1 : -1;

      if (forgottenSortKey === "display_name") {
        return (
          direction *
          (left.display_name ?? "").localeCompare(right.display_name ?? "")
        );
      }

      const leftValue = forgottenSortKey === "days_since_last_communication"
        ? left.days_since_last_communication
        : left.ranking_score;
      const rightValue = forgottenSortKey === "days_since_last_communication"
        ? right.days_since_last_communication
        : right.ranking_score;

      if (leftValue === null) return rightValue === null ? 0 : 1;
      if (rightValue === null) return -1;

      return direction * (leftValue - rightValue);
    });

  const timelineContactOptions = [
    ...new Map(
      (contacts.data ?? [])
        .filter(
          (contact): contact is ContactStatistics & {
            canonical_identity_id: number;
          } => contact.canonical_identity_id !== null,
        )
        .map((contact) => [
          contact.canonical_identity_id,
          {
            canonicalIdentityId: contact.canonical_identity_id,
            displayName:
              contact.display_name ||
              contact.platform_user_id ||
              "Unnamed contact",
            platformUserId: contact.platform_user_id,
          },
        ]),
    ).values(),
  ].sort((left, right) => left.displayName.localeCompare(right.displayName));

  const noImportedData =
    overview.data?.total_imported_accounts === 0 &&
    overview.data.total_chats === 0;

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <DashboardHeader
        selectedTab={selectedTab}
        onTabSelect={setSelectedTab}
      />
      <div className="mx-auto w-full max-w-[1200px] px-7 pt-[46px] pb-[30px] max-[820px]:pt-[34px] max-sm:px-[14px] max-sm:py-[25px]">
        <DashboardIntro />
        <div
          id="overview-panel"
          role="tabpanel"
          aria-labelledby="overview-tab"
          aria-label="Overview"
          tabIndex={0}
          hidden={selectedTab !== "overview"}
        >
          <OverviewView
            overview={overview}
            noImportedData={noImportedData}
            onRetry={() => void loadOverview()}
          />
        </div>
        <div
          id="conversation-insights-panel"
          role="tabpanel"
          aria-labelledby="conversation-insights-tab"
          aria-label="Conversation insights"
          tabIndex={0}
          hidden={selectedTab !== "conversation-insights"}
        >
          <CommunicationTimelineView
            timeline={communicationTimeline}
            contactOptions={timelineContactOptions}
            selectedContactId={selectedTimelineContactId}
            onContactChange={setSelectedTimelineContactId}
            onRetry={() =>
              void loadCommunicationTimeline(selectedTimelineContactId)
            }
          />
          <ChatInsightsView
            insights={chatInsights}
            selectedChatId={selectedInsightsChatId}
            onChatChange={setSelectedInsightsChatId}
            noImportedData={noImportedData}
            onRetry={() => void loadChatInsights()}
          />
        </div>
        <div
          id="chats-panel"
          role="tabpanel"
          aria-labelledby="chats-tab"
          aria-label="Chats"
          tabIndex={0}
          hidden={selectedTab !== "chats"}
        >
          <ChatsView
            chats={chats}
            visibleChats={visibleChats}
            search={chatSearch}
            onSearchChange={setChatSearch}
            sort={chatSort}
            onSort={changeChatSort}
            hasImportedAccounts={
              (overview.data?.total_imported_accounts ?? 0) > 0
            }
            onRetry={() => void loadChats()}
          />
        </div>
        <div
          id="uploads-panel"
          role="tabpanel"
          aria-labelledby="uploads-tab"
          aria-label="Import"
          tabIndex={0}
          hidden={selectedTab !== "uploads"}
        >
          <UploadView />
        </div>
        <div
          id="contacts-panel"
          role="tabpanel"
          aria-labelledby="contacts-tab"
          aria-label="Contacts"
          tabIndex={0}
          hidden={selectedTab !== "contacts"}
        >
          <ContactsView
            contacts={contacts}
            visibleContacts={visibleContacts}
            search={contactSearch}
            onSearchChange={setContactSearch}
            sortDirection={contactSortDirection}
            onSort={() =>
              setContactSortDirection((direction) =>
                direction === "asc" ? "desc" : "asc",
              )
            }
            hasMessages={(overview.data?.total_messages ?? 0) > 0}
            onRetry={() => void loadContacts()}
          />
        </div>
        <div
          id="identity-links-panel"
          role="tabpanel"
          aria-labelledby="identity-links-tab"
          aria-label="Identity links"
          tabIndex={0}
          hidden={selectedTab !== "identity-links"}
        >
          <IdentityLinksView
            identityLinks={identityLinks}
            onRetry={() => void loadIdentityLinks()}
            onLink={createIdentityLink}
            onUnlink={removeIdentityLink}
          />
        </div>
        <div
          id="communication-balance-panel"
          role="tabpanel"
          aria-labelledby="communication-balance-tab"
          aria-label="Balance"
          tabIndex={0}
          hidden={selectedTab !== "communication-balance"}
        >
          <CommunicationBalanceView
            balance={balance}
            visibleContacts={visibleBalanceContacts}
            search={balanceSearch}
            onSearchChange={setBalanceSearch}
            classification={balanceClassification}
            onClassificationChange={setBalanceClassification}
            sortKey={balanceSortKey}
            sortDirection={balanceSortDirection}
            onSortKeyChange={setBalanceSortKey}
            onSortDirectionChange={setBalanceSortDirection}
            onRetry={() => void loadBalance()}
          />
        </div>
        <div
          id="forgotten-contacts-panel"
          role="tabpanel"
          aria-labelledby="forgotten-contacts-tab"
          aria-label="Forgotten"
          tabIndex={0}
          hidden={selectedTab !== "forgotten-contacts"}
        >
          <ForgottenContactsView
            forgotten={forgottenContacts}
            noImportedData={noImportedData}
            visibleContacts={visibleForgottenContacts}
            search={forgottenSearch}
            onSearchChange={setForgottenSearch}
            sortKey={forgottenSortKey}
            sortDirection={forgottenSortDirection}
            onSortKeyChange={setForgottenSortKey}
            onSortDirectionChange={setForgottenSortDirection}
            onRetry={() => void loadForgottenContacts()}
          />
        </div>
        <footer className="px-0 pt-[6px] pb-3 text-center text-caption text-ink-footer">
          Statistics are aggregated from imported data. Message contents are not shown.
        </footer>
      </div>
    </main>
  );
}
