import type { ChatInsightsStatistics } from "../api";
import type { useDashboardData } from "../hooks/useDashboardData";
import type { useDashboardFilters } from "../hooks/useDashboardFilters";
import type { DashboardTab } from "../utils/dashboardTabs";
import { pageForSearchOption } from "../utils/dashboard";
import type { SearchPickerOption } from "./SearchPicker";
import { ChatsView } from "./ChatsView";
import { ChatInsightsView } from "./ChatInsightsView";

export function DashboardConversationPanels({
  dashboard,
  filters,
  selectedTab,
  selectedInsightsChatId,
  onSelectedInsightsChatChange,
  selectedChat,
  onOpenChatInsights,
  noImportedData,
  chatOptions,
}: {
  dashboard: ReturnType<typeof useDashboardData>;
  filters: ReturnType<typeof useDashboardFilters>;
  selectedTab: DashboardTab;
  selectedInsightsChatId: number | null;
  onSelectedInsightsChatChange: (chatId: number | null) => void;
  selectedChat: ChatInsightsStatistics | undefined;
  onOpenChatInsights: (chatId: number) => void;
  noImportedData: boolean;
  chatOptions: SearchPickerOption[];
}) {
  const {
    overview,
    chats,
    chatInsights,
    communicationTimeline,
    loadChats,
    loadChatInsights,
    loadCommunicationTimeline,
  } = dashboard;
  const {
    chatSearch,
    setChatSearch,
    chatPlatformFilter,
    setChatPlatformFilter,
    chatSort,
    changeChatSort,
    visibleChats,
  } = filters;

  const renderChatsView = (chatScope: "dm" | "group") => (
    <ChatsView
      chats={chats}
      chatScope={chatScope}
      visibleChats={visibleChats}
      search={chatSearch}
      platformFilter={chatPlatformFilter}
      searchOptions={chatOptions}
      onSearchChange={(value) => {
        setChatSearch(value);
        void loadChats(
          false,
          pageForSearchOption(
            value,
            chats.data?.options,
            chats.data?.pagination.page_size,
            chatPlatformFilter,
          ),
          chatSort.key,
          chatSort.direction,
          chatScope,
          chatPlatformFilter,
        );
      }}
      onPlatformFilterChange={(platform) => {
        setChatPlatformFilter(platform);
        setChatSearch("");
        void loadChats(
          false,
          1,
          chatSort.key,
          chatSort.direction,
          chatScope,
          platform,
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
        void loadChats(
          false,
          1,
          next.key,
          next.direction,
          chatScope,
          chatPlatformFilter,
        );
      }}
      hasImportedAccounts={
        (overview.data?.total_imported_accounts ?? 0) > 0
      }
      onRetry={() =>
        void loadChats(
          true,
          1,
          chatSort.key,
          chatSort.direction,
          chatScope,
          chatPlatformFilter,
        )
      }
      onPageChange={(page) => {
        setChatSearch("");
        void loadChats(
          false,
          page,
          chatSort.key,
          chatSort.direction,
          chatScope,
          chatPlatformFilter,
        );
      }}
      onOpenChatInsights={onOpenChatInsights}
    />
  );

  return (
    <>
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
            onRetryTimeline={(chatId, senderId) =>
              void loadCommunicationTimeline(undefined, chatId, senderId)
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
    </>
  );
}
