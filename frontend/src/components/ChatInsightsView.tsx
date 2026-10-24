import type { ChatInsightsResponse } from "../api";
import { formatNumber } from "../format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../styles";
import type { Resource } from "../types";
import { LoadingMessage, SectionError } from "./Feedback";
import { ChatInsightsDetails } from "./ChatInsightsDetails";
import { useChatInsights } from "./useChatInsights";

export function ChatInsightsView({
  insights,
  selectedChatId,
  onChatChange,
  noImportedData,
  onRetry,
}: {
  insights: Resource<ChatInsightsResponse>;
  selectedChatId: number | null;
  onChatChange: (chatId: number) => void;
  noImportedData: boolean | undefined;
  onRetry: () => void;
}) {
  const {
    chatSearch,
    trimmedChatSearch,
    onChatSearchChange,
    matchingChats,
    selectedChat,
  } = useChatInsights(insights, selectedChatId);

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
        {insights.data && insights.data.chats.length > 0 && (
          <div className="w-full max-w-[420px]">
            <label className="sr-only" htmlFor="chat-insights-search">
              Search chats by title
            </label>
            <input
              id="chat-insights-search"
              className="w-full rounded-md border border-border-subtle bg-surface px-3 py-2 text-small text-ink"
              type="search"
              placeholder="Search chats"
              value={chatSearch}
              onChange={(event) => onChatSearchChange(event.target.value)}
            />
            <div
              className="mt-2 max-h-56 overflow-y-auto rounded-md border border-border-subtle bg-surface"
              role="group"
              aria-label="Matching chats"
            >
              {matchingChats.map((chat) => (
                <button
                  className={`flex w-full items-center justify-between gap-3 border-0 border-b border-border-subtle px-3 py-2 text-left last:border-b-0 hover:bg-surface-muted focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-[-3px] ${
                    selectedChat?.chat_id === chat.chat_id
                      ? "bg-surface-brand text-brand-strong"
                      : "bg-surface text-ink"
                  }`}
                  key={chat.chat_id}
                  type="button"
                  aria-pressed={selectedChat?.chat_id === chat.chat_id}
                  onClick={() => onChatChange(chat.chat_id)}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-small font-semibold">
                      {chat.title || "Untitled chat"}
                    </span>
                    <span className="block truncate text-caption text-ink-muted">
                      {chat.chat_type} · {chat.source_account_label}
                    </span>
                  </span>
                  <span className="shrink-0 text-caption">
                    {formatNumber(chat.ordinary_message_count)} messages
                  </span>
                </button>
              ))}
              {matchingChats.length === 0 && (
                <p className="m-0 px-3 py-3 text-small text-ink-muted">
                  No chats match “{trimmedChatSearch}”.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {insights.loading && insights.data === null && <LoadingMessage />}
      {insights.error && (
        <SectionError message={insights.error} onRetry={onRetry} />
      )}
      {noImportedData && insights.data && (
        <p className="text-small text-ink-muted">
          Import a Telegram export to see text and reaction insights.
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
        <ChatInsightsDetails chat={selectedChat} />
      ) : null}
    </section>
  );
}
