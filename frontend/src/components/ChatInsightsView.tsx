import type {
  ChatInsightsResponse,
  CommunicationTimelineStatistics,
} from "../api";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../constants";
import type { Resource } from "../types";
import {
  LoadingMessage,
  SectionError,
} from "./Feedback";
import { ChatInsightsDetails } from "./ChatInsightsDetails";
import { CommunicationTimelineView } from "./CommunicationTimelineView";
import {
  getSelectedChatInsights,
  sortChatInsightsChats,
} from "../utils/chatInsights";
import { SearchPicker } from "./SearchPicker";

export function ChatInsightsView({
  insights,
  timeline,
  selectedChatId,
  onChatChange,
  noImportedData,
  onRetryInsights,
  onRetryTimeline,
}: {
  insights: Resource<ChatInsightsResponse>;
  timeline: Resource<CommunicationTimelineStatistics>;
  selectedChatId: number | null;
  onChatChange: (chatId: number | null) => void;
  noImportedData: boolean | undefined;
  onRetryInsights: () => void;
  onRetryTimeline: () => void;
}) {
  const sortedChats = sortChatInsightsChats(insights.data?.chats ?? []);
  const selectedChat = getSelectedChatInsights(sortedChats, selectedChatId);
  const timelineMatchesSelectedChat =
    selectedChat !== undefined &&
    timeline.data?.summary.chat_id === selectedChat.chat_id;
  const selectedTimeline: Resource<CommunicationTimelineStatistics> =
    timelineMatchesSelectedChat
      ? timeline
      : {
          data: null,
          error: timeline.data === null ? timeline.error : null,
          loading: timeline.loading || timeline.data !== null,
        };

  return (
    <section
      id="chat-insights"
      className={sectionClassName}
      aria-labelledby="chat-insights-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>WORDS & REACTIONS</p>
          <h2 id="chat-insights-title" className={sectionTitleClassName}>
            Chat insights
          </h2>
        </div>
        {insights.data &&
          ((insights.data.options?.length ?? 0) > 0 ||
            insights.data.chats.length > 0) && (
          <div className="w-full max-w-[420px]">
            <SearchPicker
              label="Choose an insight chat"
              value={selectedChat ? String(selectedChat.chat_id) : ""}
              options={insights.data.options?.length
                ? insights.data.options.map((option) => ({
                    value: option.value,
                    label: option.label,
                    platforms: option.platforms,
                    searchTerms: option.search_terms,
                  }))
                : sortedChats.map((chat) => ({
                    value: String(chat.chat_id),
                    label: chat.title || "Untitled chat",
                    platforms: [chat.platform],
                    searchTerms: [
                      chat.chat_type,
                      chat.source_account_label,
                      String(chat.chat_id),
                    ],
                  }))}
              onChange={(value) =>
                onChatChange(value === "" ? null : Number(value))
              }
              placeholder="Select a chat"
              searchPlaceholder="Search chat title or ID"
              allLabel="Default chat"
              emptyMessage="No chats match these filters."
            />
          </div>
        )}
      </div>

      {insights.loading && insights.data === null && <LoadingMessage />}
      {insights.error && (
        <SectionError message={insights.error} onRetry={onRetryInsights} />
      )}
      {noImportedData && insights.data && (
        <p className="text-small text-ink-muted">
          Import messaging exports to see text and reaction insights.
        </p>
      )}
      {insights.data && insights.data.chats.length === 0 ? (
        <div className={`${emptyStateClassName} p-[23px]`}>
          <h3 className={emptyStateTitleClassName}>No eligible chats available</h3>
          <p className={emptyStateTextClassName}>
            Insights include one-to-one personal chats, private groups, and private
            supergroups.
          </p>
        </div>
      ) : selectedChat ? (
        <>
          <CommunicationTimelineView
            timeline={selectedTimeline}
            onRetry={onRetryTimeline}
          />
          <ChatInsightsDetails
            chat={selectedChat}
            timeline={selectedTimeline.data}
          />
        </>
      ) : null}
    </section>
  );
}
