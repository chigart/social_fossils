import { useRef, useState } from "react";
import {
  getGroupInteraction,
  type ChatInsightsStatistics,
  type ForgottenContact,
} from "../api";
import type { useDashboardData } from "../hooks/useDashboardData";
import type { useDashboardFilters } from "../hooks/useDashboardFilters";
import { useViewSearchOptions } from "../hooks/useViewSearchOptions";
import type { DashboardTab } from "../utils/dashboardTabs";
import { pageForSearchOption } from "../utils/dashboard";
import { DashboardConversationPanels } from "./DashboardConversationPanels";
import { AIChatPanel } from "./AIChatPanel";
import { CommunicationBalanceView } from "./CommunicationBalanceView";
import { ContactsView } from "./ContactsView";
import { DashboardHeader } from "./DashboardHeader";
import { DashboardIntro } from "./DashboardIntro";
import { ForgottenContactsView } from "./ForgottenContactsView";
import { IdentityLinksView } from "./IdentityLinksView";
import { OverviewView } from "./OverviewView";
import { UploadView } from "./UploadView";
import type { Resource } from "../types";

export function DashboardContent({
  dashboard,
  filters,
  selectedTab,
  onTabSelect,
  selectedInsightsChatId,
  onSelectedInsightsChatChange,
  selectedChat,
  selectedTimelineAccountId,
  onTimelineAccountChange,
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
  selectedTimelineAccountId: number | null;
  onTimelineAccountChange: (accountId: number | null) => void;
  onOpenChatInsights: (chatId: number) => void;
  noImportedData: boolean;
}) {
  const [selectedInteraction, setSelectedInteraction] = useState<{
    id: number;
    resource: Resource<ForgottenContact>;
  } | null>(null);
  const interactionRequestId = useRef(0);
  const clearSelectedInteraction = () => {
    interactionRequestId.current += 1;
    setSelectedInteraction(null);
  };
  const loadSelectedInteraction = async (id: number) => {
    const requestId = ++interactionRequestId.current;
    setSelectedInteraction({
      id,
      resource: { data: null, error: null, loading: true },
    });
    try {
      const data = await getGroupInteraction(id);
      if (requestId === interactionRequestId.current) {
        setSelectedInteraction({ id, resource: { data, error: null, loading: false } });
      }
    } catch (error) {
      if (requestId === interactionRequestId.current) {
        setSelectedInteraction({
          id,
          resource: {
            data: null,
            error:
              error instanceof Error
                ? error.message
                : "Unable to load group interaction.",
            loading: false,
          },
        });
      }
    }
  };
  const {
    overview,
    communicationTimeline,
    closeFriendsTimeline,
    chats,
    contacts,
    balance,
    forgottenContacts,
    identityLinks,
    loadOverview,
    loadCommunicationTimeline,
    loadCloseFriendsTimeline,
    loadContacts,
    loadBalance,
    loadForgottenContacts,
    loadIdentityLinks,
    createIdentityLink,
    removeIdentityLink,
  } = dashboard;
  const {
    contactSearch,
    setContactSearch,
    contactPlatformFilter,
    setContactPlatformFilter,
    contactFriendStatusFilter,
    setContactFriendStatusFilter,
    balanceSearch,
    setBalanceSearch,
    balancePlatformFilter,
    setBalancePlatformFilter,
    forgottenSearch,
    setForgottenSearch,
    forgottenPlatformFilter,
    setForgottenPlatformFilter,
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
    contactSort,
    changeContactSort,
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
    clearSelectedInteraction();
    setForgottenSortKey(sortKey);
    setForgottenSortDirection(direction);
    void loadForgottenContacts(
      false,
      1,
      sortKey,
      direction,
      scope,
      forgottenPlatformFilter,
    );
  };
  const selectedInteractionId = forgottenContacts.data?.options.find(
    (option) => option.value === forgottenSearch,
  )?.contact_id;
  const interactionSelection =
    selectedTab === "interactions" &&
    forgottenSearch &&
    selectedInteraction !== null &&
    selectedInteractionId === selectedInteraction.id
      ? selectedInteraction.resource
      : null;
  const renderForgottenView = (scope: "private" | "group") => (
    <ForgottenContactsView
      forgotten={forgottenContacts}
      scope={scope}
      noImportedData={noImportedData}
      visibleContacts={
        interactionSelection
          ? interactionSelection.data
            ? [interactionSelection.data]
            : []
          : visibleForgottenContacts
      }
      selection={scope === "group" ? interactionSelection : null}
      onRetrySelection={() => {
        if (selectedInteractionId !== undefined) {
          void loadSelectedInteraction(selectedInteractionId);
        }
      }}
      search={forgottenSearch}
      platformFilter={forgottenPlatformFilter}
      searchOptions={forgottenOptions}
      onSearchChange={(value) => {
        setForgottenSearch(value);
        clearSelectedInteraction();
        const option = forgottenContacts.data?.options.find(
          (item) => item.value === value,
        );
        if (scope === "group" && value && option?.contact_id !== undefined) {
          if (
            !forgottenContacts.data?.contacts.some(
              (contact) => contact.contact_id === option.contact_id,
            )
          ) {
            void loadSelectedInteraction(option.contact_id);
          }
          return;
        }
        void loadForgottenContacts(
          false,
          pageForSearchOption(
            value,
            forgottenContacts.data?.options,
            forgottenContacts.data?.pagination.page_size,
            forgottenPlatformFilter,
            true,
          ),
          forgottenSortKey,
          forgottenSortDirection,
          scope,
          forgottenPlatformFilter,
        );
      }}
      onPlatformFilterChange={(platform) => {
        setForgottenPlatformFilter(platform);
        setForgottenSearch("");
        clearSelectedInteraction();
        void loadForgottenContacts(
          false,
          1,
          forgottenSortKey,
          forgottenSortDirection,
          scope,
          platform,
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
          forgottenPlatformFilter,
        )
      }
      onPageChange={(page) => {
        setForgottenSearch("");
        clearSelectedInteraction();
        void loadForgottenContacts(
          false,
          page,
          forgottenSortKey,
          forgottenSortDirection,
          scope,
          forgottenPlatformFilter,
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
              timeline={communicationTimeline}
              closeFriendsTimeline={closeFriendsTimeline}
              noImportedData={noImportedData}
              selectedTimelineAccountId={selectedTimelineAccountId}
              onRetry={() => void loadOverview(true)}
              onRetryTimeline={(accountId) =>
                void loadCommunicationTimeline(
                  undefined,
                  undefined,
                  undefined,
                  accountId ?? undefined,
                )
              }
              onRetryCloseFriendsTimeline={() =>
                void loadCloseFriendsTimeline()
              }
              onTimelineAccountChange={onTimelineAccountChange}
            />
          )}
        </div>
        <DashboardConversationPanels
          dashboard={dashboard}
          filters={filters}
          selectedTab={selectedTab}
          selectedInsightsChatId={selectedInsightsChatId}
          onSelectedInsightsChatChange={onSelectedInsightsChatChange}
          selectedChat={selectedChat}
          onOpenChatInsights={onOpenChatInsights}
          noImportedData={noImportedData}
          chatOptions={chatOptions}
        />
        <div
          id="ai-panel"
          role="tabpanel"
          aria-labelledby="ai-tab"
          aria-label="AI"
          tabIndex={0}
          hidden={selectedTab !== "ai"}
        >
          <AIChatPanel active={selectedTab === "ai"} />
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
              platformFilter={contactPlatformFilter}
              friendStatusFilter={contactFriendStatusFilter}
              searchOptions={contactOptions}
              onSearchChange={(value) => {
                setContactSearch(value);
                void loadContacts(
                  false,
                  pageForSearchOption(
                    value,
                    contacts.data?.options,
                    contacts.data?.pagination.page_size,
                    contactPlatformFilter,
                    true,
                  ),
                  contactSort.key,
                  contactSort.direction,
                  contactPlatformFilter,
                  contactFriendStatusFilter,
                );
              }}
              onPlatformFilterChange={(platform) => {
                setContactPlatformFilter(platform);
                setContactSearch("");
                void loadContacts(
                  false,
                  1,
                  contactSort.key,
                  contactSort.direction,
                  platform,
                  contactFriendStatusFilter,
                );
              }}
              onFriendStatusFilterChange={(friendStatus) => {
                setContactFriendStatusFilter(friendStatus);
                setContactSearch("");
                void loadContacts(
                  false,
                  1,
                  contactSort.key,
                  contactSort.direction,
                  contactPlatformFilter,
                  friendStatus,
                );
              }}
              sort={contactSort}
              onSort={(key) => {
                setContactSearch("");
                const next = {
                  key,
                  direction:
                    contactSort.key === key &&
                    contactSort.direction === "asc"
                      ? "desc"
                      : "asc",
                } as const;
                changeContactSort(key);
                void loadContacts(
                  false,
                  1,
                  next.key,
                  next.direction,
                  contactPlatformFilter,
                  contactFriendStatusFilter,
                );
              }}
              hasMessages={(overview.data?.total_messages ?? 0) > 0}
              onRetry={() =>
                void loadContacts(
                  true,
                  1,
                  contactSort.key,
                  contactSort.direction,
                  contactPlatformFilter,
                  contactFriendStatusFilter,
                )
              }
              onPageChange={(page) => {
                setContactSearch("");
                void loadContacts(
                  false,
                  page,
                  contactSort.key,
                  contactSort.direction,
                  contactPlatformFilter,
                  contactFriendStatusFilter,
                );
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
              platformFilter={balancePlatformFilter}
              searchOptions={balanceOptions}
              onSearchChange={(value) => {
                setBalanceSearch(value);
                void loadBalance(
                  false,
                  pageForSearchOption(
                    value,
                    balance.data?.options,
                    balance.data?.pagination.page_size,
                    balancePlatformFilter,
                    true,
                  ),
                  balanceSortKey,
                  balanceSortDirection,
                  balanceClassification,
                  balancePlatformFilter,
                );
              }}
              onPlatformFilterChange={(platform) => {
                setBalancePlatformFilter(platform);
                setBalanceSearch("");
                void loadBalance(
                  false,
                  1,
                  balanceSortKey,
                  balanceSortDirection,
                  balanceClassification,
                  platform,
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
                  balancePlatformFilter,
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
                  balancePlatformFilter,
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
                  balancePlatformFilter,
                );
              }}
              onRetry={() =>
                void loadBalance(
                  true,
                  1,
                  balanceSortKey,
                  balanceSortDirection,
                  balanceClassification,
                  balancePlatformFilter,
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
                  balancePlatformFilter,
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
