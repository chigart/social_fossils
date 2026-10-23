import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../format";
import {
  chatInsightsCardClassName,
  chatInsightsEmptyTextClassName,
  chatInsightsGridClassName,
  chatInsightsSectionTitleClassName,
} from "../styles";
import { MetricCard } from "./Feedback";
import { SenderRankings } from "./SenderRankings";
import { ConversationFlow } from "./ConversationFlow";
import { MessageTypeBreakdown } from "./MessageTypeBreakdown";
import { ReactionAnalytics } from "./ReactionAnalytics";
import { RankingChips } from "./RankingChips";
import { SenderAverageLengthChart } from "./SenderAverageLengthChart";
import { SenderShareChart } from "./SenderShareChart";
import { filterRepeatedItems } from "./chatInsightsUtils";

export function ChatInsightsDetails({ chat }: { chat: ChatInsightsStatistics }) {
  const popularWords = filterRepeatedItems(chat.popular_words);
  const popularEmojis = filterRepeatedItems(chat.popular_emojis);

  return (
    <>
      <div className="mb-5 grid grid-cols-3 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
        <MetricCard
          label="Ordinary messages"
          value={formatNumber(chat.ordinary_message_count)}
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
      <ConversationFlow chat={chat} />
      <MessageTypeBreakdown chat={chat} />
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
      <ReactionAnalytics chat={chat} />
    </>
  );
}
