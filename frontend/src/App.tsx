import { useEffect, useMemo, useState } from "react";
import { ChatsView } from "./components/ChatsView";
import { ChatInsightsView } from "./components/ChatInsightsView";
import { CommunicationBalanceView } from "./components/CommunicationBalanceView";
import { ContactsView } from "./components/ContactsView";
import { DashboardHeader } from "./components/DashboardHeader";
import { DashboardIntro } from "./components/DashboardIntro";
import { ForgottenContactsView } from "./components/ForgottenContactsView";
import { IdentityLinksView } from "./components/IdentityLinksView";
import { OverviewView } from "./components/OverviewView";
import { UploadView } from "./components/UploadView";
import {
  getSelectedChatInsights,
  sortChatInsightsChats,
} from "./components/chatInsightsUtils";
import {
  dashboardTabFromHash,
  type DashboardTab,
} from "./components/dashboardTabs";
import { useDashboardData } from "./hooks/useDashboardData";
import { useDashboardFilters } from "./hooks/useDashboardFilters";

function pageForSearchOption(
  value: string,
  options: { value: string }[] | undefined,
  pageSize: number | undefined,
): number {
  if (!value || !options || !pageSize) return 1;
  const index = options.findIndex((option) => option.value === value);
  return index < 0 ? 1 : Math.floor(index / pageSize) + 1;
}

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
  } = filters;
  const sortedInsightChats = useMemo(
    () => sortChatInsightsChats(chatInsights.data?.chats ?? []),
    [chatInsights.data],
  );
  const selectedChat = useMemo(
    () => getSelectedChatInsights(sortedInsightChats, selectedInsightsChatId),
    [sortedInsightChats, selectedInsightsChatId],
  );

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

  useEffect(() => {
    switch (selectedTab) {
      case "overview":
        void loadOverview();
        break;
      case "conversation-insights":
        void loadOverview();
        void loadChatInsights(false, selectedInsightsChatId ?? undefined);
        break;
      case "chats":
        void loadOverview();
        void loadChats(
          false,
          chats.data?.pagination.page ?? 1,
          chatSort.key,
          chatSort.direction,
        );
        break;
      case "contacts":
        void loadOverview();
        void loadContacts(
          false,
          contacts.data?.pagination.page ?? 1,
          contactSortDirection,
        );
        break;
      case "identity-links":
        void loadIdentityLinks();
        break;
      case "communication-balance":
        void loadBalance(
          false,
          balance.data?.pagination.page ?? 1,
          balanceSortKey,
          balanceSortDirection,
          balanceClassification,
        );
        break;
      case "forgotten-contacts":
        void loadOverview();
        void loadForgottenContacts(
          false,
          forgottenContacts.data?.pagination.page ?? 1,
          forgottenSortKey,
          forgottenSortDirection,
        );
        break;
      case "uploads":
        break;
    }
  }, [
    selectedTab,
    selectedInsightsChatId,
    chats.data?.pagination.page,
    contacts.data?.pagination.page,
    balance.data?.pagination.page,
    forgottenContacts.data?.pagination.page,
    loadOverview,
    loadChats,
    loadChatInsights,
    loadContacts,
    loadIdentityLinks,
    loadBalance,
    loadForgottenContacts,
  ]);

  useEffect(() => {
    if (selectedChat) {
      void loadCommunicationTimeline(undefined, selectedChat.chat_id);
    }
  }, [selectedChat?.chat_id, loadCommunicationTimeline]);

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
          {selectedTab === "overview" && (
            <OverviewView
              overview={overview}
              noImportedData={noImportedData}
              onRetry={() => void loadOverview(true)}
            />
          )}
        </div>
        <div
          id="conversation-insights-panel"
          role="tabpanel"
          aria-labelledby="conversation-insights-tab"
          aria-label="Conversation insights"
          tabIndex={0}
          hidden={selectedTab !== "conversation-insights"}
        >
          {selectedTab === "conversation-insights" && (
            <ChatInsightsView
              insights={chatInsights}
              timeline={communicationTimeline}
              selectedChatId={selectedInsightsChatId}
              onChatChange={(chatId) => {
                setSelectedInsightsChatId(chatId);
              }}
              noImportedData={noImportedData}
              onRetryInsights={() =>
                void loadChatInsights(
                  true,
                  selectedInsightsChatId ?? undefined,
                )
              }
              onRetryTimeline={() =>
                void loadCommunicationTimeline(undefined, selectedChat?.chat_id)
              }
            />
          )}
        </div>
        <div
          id="chats-panel"
          role="tabpanel"
          aria-labelledby="chats-tab"
          aria-label="Chats"
          tabIndex={0}
          hidden={selectedTab !== "chats"}
        >
          {selectedTab === "chats" && (
            <ChatsView
              chats={chats}
              visibleChats={visibleChats}
              search={chatSearch}
              onSearchChange={(value) => {
                setChatSearch(value);
                void loadChats(
                  false,
                  pageForSearchOption(
                    value,
                    chats.data?.options,
                    chats.data?.pagination.page_size,
                  ),
                  chatSort.key,
                  chatSort.direction,
                );
              }}
              sort={chatSort}
              onSort={(key) => {
                setChatSearch("");
                const next = {
                  key,
                  direction:
                    chatSort.key === key && chatSort.direction === "asc"
                      ? "desc"
                      : "asc",
                } as const;
                changeChatSort(key);
                void loadChats(false, 1, next.key, next.direction);
              }}
              hasImportedAccounts={
                (overview.data?.total_imported_accounts ?? 0) > 0
              }
              onRetry={() =>
                void loadChats(true, 1, chatSort.key, chatSort.direction)
              }
              onPageChange={(page) => {
                setChatSearch("");
                void loadChats(
                  false,
                  page,
                  chatSort.key,
                  chatSort.direction,
                );
              }}
            />
          )}
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
          {selectedTab === "contacts" && (
            <ContactsView
              contacts={contacts}
              visibleContacts={visibleContacts}
              search={contactSearch}
              onSearchChange={(value) => {
                setContactSearch(value);
                void loadContacts(
                  false,
                  pageForSearchOption(
                    value,
                    contacts.data?.options,
                    contacts.data?.pagination.page_size,
                  ),
                  contactSortDirection,
                );
              }}
              sortDirection={contactSortDirection}
              onSort={() => {
                setContactSearch("");
                const next = contactSortDirection === "asc" ? "desc" : "asc";
                setContactSortDirection(next);
                void loadContacts(false, 1, next);
              }}
              hasMessages={(overview.data?.total_messages ?? 0) > 0}
              onRetry={() =>
                void loadContacts(true, 1, contactSortDirection)
              }
              onPageChange={(page) => {
                setContactSearch("");
                void loadContacts(false, page, contactSortDirection);
              }}
            />
          )}
        </div>
        <div
          id="identity-links-panel"
          role="tabpanel"
          aria-labelledby="identity-links-tab"
          aria-label="Identity links"
          tabIndex={0}
          hidden={selectedTab !== "identity-links"}
        >
          {selectedTab === "identity-links" && (
            <IdentityLinksView
              identityLinks={identityLinks}
              onRetry={() => void loadIdentityLinks(true)}
              onLink={createIdentityLink}
              onUnlink={removeIdentityLink}
            />
          )}
        </div>
        <div
          id="communication-balance-panel"
          role="tabpanel"
          aria-labelledby="communication-balance-tab"
          aria-label="Balance"
          tabIndex={0}
          hidden={selectedTab !== "communication-balance"}
        >
          {selectedTab === "communication-balance" && (
            <CommunicationBalanceView
              balance={balance}
              visibleContacts={visibleBalanceContacts}
              search={balanceSearch}
              onSearchChange={(value) => {
                setBalanceSearch(value);
                void loadBalance(
                  false,
                  pageForSearchOption(
                    value,
                    balance.data?.options,
                    balance.data?.pagination.page_size,
                  ),
                  balanceSortKey,
                  balanceSortDirection,
                  balanceClassification,
                );
              }}
              classification={balanceClassification}
              onClassificationChange={(classification) => {
                setBalanceSearch("");
                setBalanceClassification(classification);
                void loadBalance(
                  false,
                  1,
                  balanceSortKey,
                  balanceSortDirection,
                  classification,
                );
              }}
              sortKey={balanceSortKey}
              sortDirection={balanceSortDirection}
              onSortKeyChange={(sortKey) => {
                setBalanceSearch("");
                setBalanceSortKey(sortKey);
                void loadBalance(
                  false,
                  1,
                  sortKey,
                  balanceSortDirection,
                  balanceClassification,
                );
              }}
              onSortDirectionChange={(direction) => {
                setBalanceSearch("");
                setBalanceSortDirection(direction);
                void loadBalance(
                  false,
                  1,
                  balanceSortKey,
                  direction,
                  balanceClassification,
                );
              }}
              onRetry={() =>
                void loadBalance(
                  true,
                  1,
                  balanceSortKey,
                  balanceSortDirection,
                  balanceClassification,
                )
              }
              onPageChange={(page) => {
                setBalanceSearch("");
                void loadBalance(
                  false,
                  page,
                  balanceSortKey,
                  balanceSortDirection,
                  balanceClassification,
                );
              }}
            />
          )}
        </div>
        <div
          id="forgotten-contacts-panel"
          role="tabpanel"
          aria-labelledby="forgotten-contacts-tab"
          aria-label="Forgotten"
          tabIndex={0}
          hidden={selectedTab !== "forgotten-contacts"}
        >
          {selectedTab === "forgotten-contacts" && (
            <ForgottenContactsView
              forgotten={forgottenContacts}
              noImportedData={noImportedData}
              visibleContacts={visibleForgottenContacts}
              search={forgottenSearch}
              onSearchChange={(value) => {
                setForgottenSearch(value);
                void loadForgottenContacts(
                  false,
                  pageForSearchOption(
                    value,
                    forgottenContacts.data?.options,
                    forgottenContacts.data?.pagination.page_size,
                  ),
                  forgottenSortKey,
                  forgottenSortDirection,
                );
              }}
              sortKey={forgottenSortKey}
              sortDirection={forgottenSortDirection}
              onSortKeyChange={(sortKey) => {
                setForgottenSearch("");
                setForgottenSortKey(sortKey);
                void loadForgottenContacts(
                  false,
                  1,
                  sortKey,
                  forgottenSortDirection,
                );
              }}
              onSortDirectionChange={(direction) => {
                setForgottenSearch("");
                setForgottenSortDirection(direction);
                void loadForgottenContacts(
                  false,
                  1,
                  forgottenSortKey,
                  direction,
                );
              }}
              onRetry={() =>
                void loadForgottenContacts(
                  true,
                  1,
                  forgottenSortKey,
                  forgottenSortDirection,
                )
              }
              onPageChange={(page) => {
                setForgottenSearch("");
                void loadForgottenContacts(
                  false,
                  page,
                  forgottenSortKey,
                  forgottenSortDirection,
                );
              }}
            />
          )}
        </div>
        <footer className="px-0 pt-[6px] pb-3 text-center text-caption text-ink-footer">
          Statistics are aggregated from imported data. Message contents are not shown.
        </footer>
      </div>
    </main>
  );
}
