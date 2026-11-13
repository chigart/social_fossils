import type { ChatInsightsStatistics } from "../api";
import type { useDashboardData } from "../hooks/useDashboardData";
import type { useDashboardFilters } from "../hooks/useDashboardFilters";
import { useViewSearchOptions } from "../hooks/useViewSearchOptions";
import type { DashboardTab } from "../utils/dashboardTabs";
import { pageForSearchOption } from "../utils/dashboard";
import { ChatsView } from "./ChatsView";
import { ChatInsightsView } from "./ChatInsightsView";
import { CommunicationBalanceView } from "./CommunicationBalanceView";
import { ContactsView } from "./ContactsView";
import { DashboardHeader } from "./DashboardHeader";
import { DashboardIntro } from "./DashboardIntro";
import { ForgottenContactsView } from "./ForgottenContactsView";
import { IdentityLinksView } from "./IdentityLinksView";
import { OverviewView } from "./OverviewView";
import { UploadView } from "./UploadView";

export function DashboardContent({
  dashboard,
  filters,
  selectedTab,
  onTabSelect,
  selectedInsightsChatId,
  onSelectedInsightsChatChange,
  selectedChat,
  onOpenChatInsights,
  noImportedData,
}: {
  dashboard: ReturnType<typeof useDashboardData>;
  filters: ReturnType<typeof useDashboardFilters>;
  selectedTab: DashboardTab;
  onTabSelect: (tab: DashboardTab) => void;
  selectedInsightsChatId: number | null;
  onSelectedInsightsChatChange: (chatId: number | null) => void;
  selectedChat: ChatInsightsStatistics | undefined;
  onOpenChatInsights: (chatId: number) => void;
  noImportedData: boolean;
}) {
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
  const { chatOptions, contactOptions, balanceOptions, forgottenOptions } =
    useViewSearchOptions({
      chats: chats.data,
      contacts: contacts.data,
      balance: balance.data,
      forgotten: forgottenContacts.data,
    });
  const renderChatsView = (chatScope: "dm" | "group") => (
    <ChatsView
      chats={chats}
      chatScope={chatScope}
      visibleChats={visibleChats}
      search={chatSearch}
      searchOptions={chatOptions}
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
          chatScope,
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
        void loadChats(false, 1, next.key, next.direction, chatScope);
      }}
      hasImportedAccounts={
        (overview.data?.total_imported_accounts ?? 0) > 0
      }
      onRetry={() =>
        void loadChats(true, 1, chatSort.key, chatSort.direction, chatScope)
      }
      onPageChange={(page) => {
        setChatSearch("");
        void loadChats(false, page, chatSort.key, chatSort.direction, chatScope);
      }}
      onOpenChatInsights={onOpenChatInsights}
    />
  );
  const changeForgottenSort = (
    sortKey:
      | "ranking_score"
      | "display_name"
      | "days_since_last_communication",
    defaultDirection: "asc" | "desc",
    scope: "private" | "group",
  ) => {
    const direction =
      forgottenSortKey === sortKey
        ? forgottenSortDirection === "asc"
          ? "desc"
          : "asc"
        : defaultDirection;
    setForgottenSearch("");
    setForgottenSortKey(sortKey);
    setForgottenSortDirection(direction);
    void loadForgottenContacts(false, 1, sortKey, direction, scope);
  };
  const renderForgottenView = (scope: "private" | "group") => (
    <ForgottenContactsView
      forgotten={forgottenContacts}
      scope={scope}
      noImportedData={noImportedData}
      visibleContacts={visibleForgottenContacts}
      search={forgottenSearch}
      searchOptions={forgottenOptions}
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
          scope,
        );
      }}
      sortKey={forgottenSortKey}
      sortDirection={forgottenSortDirection}
      onSortByRank={() =>
        changeForgottenSort("ranking_score", "desc", scope)
      }
      onSortByLastSeen={() =>
        changeForgottenSort(
          "days_since_last_communication",
          "desc",
          scope,
        )
      }
      onSortByName={() =>
        changeForgottenSort("display_name", "asc", scope)
      }
      onRetry={() =>
        void loadForgottenContacts(
          true,
          1,
          forgottenSortKey,
          forgottenSortDirection,
          scope,
        )
      }
      onPageChange={(page) => {
        setForgottenSearch("");
        void loadForgottenContacts(
          false,
          page,
          forgottenSortKey,
          forgottenSortDirection,
          scope,
        );
      }}
    />
  );

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <DashboardHeader selectedTab={selectedTab} onTabSelect={onTabSelect} />
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
          tabIndex={0}
          hidden={selectedTab !== "conversation-insights"}
        >
          {selectedTab === "conversation-insights" && (
            <ChatInsightsView
              insights={chatInsights}
              timeline={communicationTimeline}
              selectedChatId={selectedInsightsChatId}
              onChatChange={onSelectedInsightsChatChange}
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
          id="dms-panel"
          role="tabpanel"
          aria-labelledby="dms-tab"
          aria-label="DMs"
          tabIndex={0}
          hidden={selectedTab !== "dms"}
        >
          {selectedTab === "dms" && renderChatsView("dm")}
        </div>
        <div
          id="chats-panel"
          role="tabpanel"
          aria-labelledby="chats-tab"
          aria-label="Chats"
          tabIndex={0}
          hidden={selectedTab !== "chats"}
        >
          {selectedTab === "chats" && renderChatsView("group")}
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
              searchOptions={contactOptions}
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
              searchOptions={balanceOptions}
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
            renderForgottenView("private")
          )}
        </div>
        <div
          id="interactions-panel"
          role="tabpanel"
          aria-labelledby="interactions-tab"
          aria-label="Interactions"
          tabIndex={0}
          hidden={selectedTab !== "interactions"}
        >
          {selectedTab === "interactions" && renderForgottenView("group")}
        </div>
        <footer className="px-0 pt-[6px] pb-3 text-center text-caption text-ink-footer">
          Statistics are aggregated from imported data. Message contents are not
          shown.
        </footer>
      </div>
    </main>
  );
}
