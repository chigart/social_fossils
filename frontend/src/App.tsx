import { useEffect, useState } from "react";
import { ChatsView } from "./components/ChatsView";
import { ChatInsightsView } from "./components/ChatInsightsView";
import { CommunicationBalanceView } from "./components/CommunicationBalanceView";
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
import { useDashboardData } from "./hooks/useDashboardData";
import { useDashboardFilters } from "./hooks/useDashboardFilters";

export default function App() {
  const dashboard = useDashboardData();
  const {
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
  } = dashboard;
  const [selectedInsightsChatId, setSelectedInsightsChatId] =
    useState<number | null>(null);
  const [selectedTab, setSelectedTab] = useState<DashboardTab>(() =>
    dashboardTabFromHash(window.location.hash),
  );
  const filters = useDashboardFilters({
    chats,
    contacts,
    balance,
    forgottenContacts,
  });
  const {
    chatSearch,
    setChatSearch,
    contactSearch,
    setContactSearch,
    balanceSearch,
    setBalanceSearch,
    forgottenSearch,
    setForgottenSearch,
    balanceClassification,
    setBalanceClassification,
    forgottenSortKey,
    setForgottenSortKey,
    forgottenSortDirection,
    setForgottenSortDirection,
    balanceSortKey,
    setBalanceSortKey,
    balanceSortDirection,
    setBalanceSortDirection,
    chatSort,
    changeChatSort,
    contactSortDirection,
    setContactSortDirection,
    visibleChats,
    visibleContacts,
    visibleBalanceContacts,
    visibleForgottenContacts,
    timelineContactOptions,
  } = filters;

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
