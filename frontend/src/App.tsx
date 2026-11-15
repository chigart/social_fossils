import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DashboardContent } from "./components/DashboardContent";
import {
  getSelectedChatInsights,
  sortChatInsightsChats,
} from "./utils/chatInsights";
import {
  dashboardTabFromHash,
  type DashboardTab,
} from "./utils/dashboardTabs";
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
    loadOverview,
    loadCommunicationTimeline,
    loadChats,
    loadChatInsights,
    loadContacts,
    loadBalance,
    loadForgottenContacts,
    loadIdentityLinks,
  } = dashboard;
  const [selectedInsightsChatId, setSelectedInsightsChatId] =
    useState<number | null>(null);
  const [selectedTimelineAccountId, setSelectedTimelineAccountId] =
    useState<number | null>(null);
  const [selectedTab, setSelectedTab] = useState<DashboardTab>(() =>
    dashboardTabFromHash(window.location.hash),
  );
  const lastChatScope = useRef<"dm" | "group" | null>(null);
  const lastForgottenScope = useRef<"private" | "group" | null>(null);
  const filters = useDashboardFilters({
    chatScope: selectedTab === "dms" ? "dm" : "group",
    chats,
    contacts,
    balance,
    forgottenContacts,
  });
  const {
    chatSort,
    chatPlatformFilter,
    contactSort,
    contactPlatformFilter,
    balanceClassification,
    balancePlatformFilter,
    balanceSortKey,
    balanceSortDirection,
    forgottenSortKey,
    forgottenSortDirection,
    forgottenPlatformFilter,
  } = filters;
  const changeTab = useCallback((tab: DashboardTab) => {
    const switchingChatScope =
      (selectedTab === "dms" && tab === "chats") ||
      (selectedTab === "chats" && tab === "dms");
    const switchingForgottenScope =
      (selectedTab === "forgotten-contacts" && tab === "interactions") ||
      (selectedTab === "interactions" && tab === "forgotten-contacts");
    if (switchingChatScope) {
      filters.setChatSearch("");
      filters.setChatPlatformFilter("");
    }
    if (switchingForgottenScope) {
      filters.setForgottenSearch("");
      filters.setForgottenPlatformFilter("");
    }
    setSelectedTab(tab);
  }, [
    filters.setChatSearch,
    filters.setChatPlatformFilter,
    filters.setForgottenSearch,
    filters.setForgottenPlatformFilter,
    selectedTab,
  ]);
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
      changeTab(dashboardTabFromHash(window.location.hash));
    window.addEventListener("hashchange", syncSelectedTab);
    window.addEventListener("popstate", syncSelectedTab);
    return () => {
      window.removeEventListener("hashchange", syncSelectedTab);
      window.removeEventListener("popstate", syncSelectedTab);
    };
  }, [changeTab]);

  useEffect(() => {
    switch (selectedTab) {
      case "overview":
        void loadOverview();
        void loadCommunicationTimeline(
          undefined,
          undefined,
          undefined,
          selectedTimelineAccountId ?? undefined,
        );
        break;
      case "conversation-insights":
        void loadOverview();
        void loadChatInsights(false, selectedInsightsChatId ?? undefined);
        break;
      case "dms":
      case "chats":
        void loadOverview();
        {
          const scope = selectedTab === "dms" ? "dm" : "group";
          const page =
            lastChatScope.current === scope
              ? chats.data?.pagination.page ?? 1
              : 1;
          lastChatScope.current = scope;
        void loadChats(
          false,
          page,
          chatSort.key,
          chatSort.direction,
          scope,
          chatPlatformFilter,
        );
        }
        break;
      case "contacts":
        void loadOverview();
        void loadContacts(
          false,
          contacts.data?.pagination.page ?? 1,
          contactSort.key,
          contactSort.direction,
          contactPlatformFilter,
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
          balancePlatformFilter,
        );
        break;
      case "forgotten-contacts":
      case "interactions":
        void loadOverview();
        {
          const scope = selectedTab === "interactions" ? "group" : "private";
          const page =
            lastForgottenScope.current === scope
              ? forgottenContacts.data?.pagination.page ?? 1
              : 1;
          lastForgottenScope.current = scope;
        void loadForgottenContacts(
          false,
          page,
          forgottenSortKey,
          forgottenSortDirection,
          scope,
          forgottenPlatformFilter,
        );
        }
        break;
      case "uploads":
        break;
    }
  }, [
    selectedTab,
    selectedInsightsChatId,
    selectedTimelineAccountId,
    loadOverview,
    loadCommunicationTimeline,
    loadChats,
    loadChatInsights,
    loadContacts,
    loadIdentityLinks,
    loadBalance,
    loadForgottenContacts,
  ]);

  useEffect(() => {
    if (selectedChat) {
      void dashboard.loadCommunicationTimeline(undefined, selectedChat.chat_id);
    }
  }, [selectedChat?.chat_id, dashboard.loadCommunicationTimeline]);

  const noImportedData =
    overview.data?.total_imported_accounts === 0 &&
    overview.data.total_chats === 0;
  const openChatInsights = (chatId: number) => {
    setSelectedInsightsChatId(chatId);
    setSelectedTab("conversation-insights");
    window.history.pushState(null, "", "#conversation-insights");
  };

  return (
    <DashboardContent
      dashboard={dashboard}
      filters={filters}
      selectedTab={selectedTab}
      onTabSelect={changeTab}
      selectedInsightsChatId={selectedInsightsChatId}
      onSelectedInsightsChatChange={setSelectedInsightsChatId}
      selectedChat={selectedChat}
      selectedTimelineAccountId={selectedTimelineAccountId}
      onTimelineAccountChange={setSelectedTimelineAccountId}
      onOpenChatInsights={openChatInsights}
      noImportedData={noImportedData}
    />
  );
}
