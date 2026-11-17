import type {
  ChatInsightsStatistics,
  CommunicationTimelineStatistics,
} from "../api";
import { formatNumber } from "../utils/format";
import {
  chatInsightsCardClassName,
  chatInsightsEmptyTextClassName,
  chatInsightsGridClassName,
  chatInsightsSectionTitleClassName,
} from "../constants";
import { MetricCard } from "./Feedback";
import { SenderRankings } from "./SenderRankings";
import { ConversationFlow } from "./ConversationFlow";
import { MessageTypeBreakdown } from "./MessageTypeBreakdown";
import { ReactionAnalytics } from "./ReactionAnalytics";
import { RankingChips } from "./RankingChips";
import { SenderAverageLengthChart } from "./SenderAverageLengthChart";
import { SenderShareChart } from "./SenderShareChart";
import { ActivityPatterns } from "./ActivityPatterns";
import { filterRepeatedItems } from "../utils/chatInsights";
import { formatResponseTime } from "../utils/formatResponseTime";

export function ChatInsightsDetails({
  chat,
  timeline,
}: {
  chat: ChatInsightsStatistics;
  timeline: CommunicationTimelineStatistics | null;
}) {
  const popularWords = filterRepeatedItems(chat.popular_words);
  const popularEmojis = filterRepeatedItems(chat.popular_emojis);
  const activeDays = timeline?.months.reduce(
    (total, month) => total + month.active_days,
    0,
  );
  const ownerMessageCount = timeline?.summary.owner_message_count;
  const contactMessageCount = timeline?.summary.contact_message_count;

  return (
    <>
      <div className="mb-5 grid grid-flow-col grid-rows-2 auto-cols-[minmax(12rem,1fr)] gap-3 overflow-x-auto max-sm:gap-2">
        <MetricCard
          label="Ordinary messages"
          value={formatNumber(chat.ordinary_message_count)}
        />
        <MetricCard
          label="Active days"
          value={activeDays === undefined ? "—" : formatNumber(activeDays)}
        />
        {chat.chat_type === "personal_chat" && (
          <>
            <MetricCard
              label="Average contact reply time"
              value={formatResponseTime(chat.reply_tempo.average_response_seconds)}
              detail={`${formatNumber(chat.reply_tempo.measured_contact_reply_session_count)} measured sessions; shown with at least 5`}
            />
            <MetricCard
              label="Longest contact reply time"
              value={formatResponseTime(chat.reply_tempo.longest_response_seconds)}
              detail="First contact reply in an owner-opened session"
            />
          </>
        )}
        <MetricCard
          label="Owner messages"
          value={
            ownerMessageCount === undefined
              ? "—"
              : formatNumber(ownerMessageCount)
          }
        />
        <MetricCard
          label="Contact messages"
          value={
            contactMessageCount === undefined
              ? "—"
              : formatNumber(contactMessageCount)
          }
        />
        <MetricCard
          label="Text volume"
          value={formatNumber(chat.text_length)}
          detail="Unicode characters"
        />
        <MetricCard
          label="Emoji reactions"
          value={formatNumber(chat.reaction_count)}
        />
      </div>
      <div className="mb-5 grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        <SenderShareChart
          title="Share of messages by person"
          senders={chat.senders}
          total={chat.ordinary_message_count}
          metric="messages"
        />
        <SenderShareChart
          title="Share of text volume by person"
          senders={chat.senders}
          total={chat.text_length}
          metric="characters"
        />
      </div>
      <div className="mb-5">
        <SenderAverageLengthChart senders={chat.senders} />
      </div>
      <ActivityPatterns
        senders={chat.senders}
        averageActivityTime={chat.average_activity_time}
        weekdayActivity={chat.weekday_activity}
        monthActivity={chat.month_activity}
      />
      <ConversationFlow chat={chat} />
      {chat.platform !== "vk" && <MessageTypeBreakdown chat={chat} />}
      <div className={chatInsightsGridClassName}>
        <section className={chatInsightsCardClassName}>
          <h3 className={chatInsightsSectionTitleClassName}>
            Most popular words
          </h3>
          {popularWords.length > 0 ? (
            <RankingChips
              items={popularWords}
              getLabel={(item) => item.word}
              countLabel="uses"
              labelClassName="font-semibold text-ink"
              countClassName="text-caption font-medium text-ink-muted"
            />
          ) : (
            <p className={chatInsightsEmptyTextClassName}>
              No words in text messages.
            </p>
          )}
        </section>
        <section className={chatInsightsCardClassName}>
          <h3 className={chatInsightsSectionTitleClassName}>
            Most popular emojis in text
          </h3>
          {popularEmojis.length > 0 ? (
            <RankingChips
              items={popularEmojis}
              getLabel={(item) => item.emoji}
              countLabel="uses"
            />
          ) : (
            <p className={chatInsightsEmptyTextClassName}>
              No emojis in text messages.
            </p>
          )}
        </section>
      </div>
      <SenderRankings chat={chat} />
      {chat.platform !== "vk" && <ReactionAnalytics chat={chat} />}
    </>
  );
}
