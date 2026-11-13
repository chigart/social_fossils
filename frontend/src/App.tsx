import { useEffect, useMemo, useState } from "react";
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
    loadChats,
    loadChatInsights,
    loadContacts,
    loadBalance,
    loadForgottenContacts,
    loadIdentityLinks,
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
    chatSort,
    contactSortDirection,
    balanceClassification,
    balanceSortKey,
    balanceSortDirection,
    forgottenSortKey,
    forgottenSortDirection,
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
      onTabSelect={setSelectedTab}
      selectedInsightsChatId={selectedInsightsChatId}
      onSelectedInsightsChatChange={setSelectedInsightsChatId}
      selectedChat={selectedChat}
      onOpenChatInsights={openChatInsights}
      noImportedData={noImportedData}
    />
  );
}
