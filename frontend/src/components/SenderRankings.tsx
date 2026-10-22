import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../format";
import {
  chatInsightsCardClassName,
  chatInsightsEmptyTextClassName,
  chatInsightsGridClassName,
  chatInsightsSectionTitleClassName,
} from "../styles";
import { filterRepeatedItems } from "./chatInsightsUtils";
import { RankingChips } from "./RankingChips";

export function SenderRankings({ chat }: { chat: ChatInsightsStatistics }) {
  return (
    <section className="mt-5" aria-labelledby="sender-rankings-title">
      <h3 id="sender-rankings-title" className="mb-3 text-subheading font-bold text-ink">
        Popular words and emojis by sender
      </h3>
      <div className={chatInsightsGridClassName}>
        {chat.senders.map((sender) => {
          const popularWords = filterRepeatedItems(sender.popular_words);
          const popularEmojis = filterRepeatedItems(sender.popular_emojis);
          return (
            <article
              className={chatInsightsCardClassName}
              key={sender.sender_telegram_id ?? "unknown"}
            >
              <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                <h4 className="m-0 text-ui font-semibold text-ink">
                  {sender.display_name}
                </h4>
                <span className="text-caption text-ink-muted">
                  {formatNumber(sender.message_count)} messages ·{" "}
                  {formatNumber(sender.text_length)} characters
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
                <section className={chatInsightsCardClassName}>
                  <h5 className={chatInsightsSectionTitleClassName}>Top words</h5>
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
                  <h5 className={chatInsightsSectionTitleClassName}>Top emojis</h5>
                  {popularEmojis.length > 0 ? (
                    <RankingChips
                      items={popularEmojis}
                      getLabel={(item) => item.emoji}
                      countLabel="uses"
                      labelClassName="text-base"
                      countClassName="text-caption font-medium text-ink-muted"
                    />
                  ) : (
                    <p className={chatInsightsEmptyTextClassName}>
                      No emojis in text messages.
                    </p>
                  )}
                </section>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
