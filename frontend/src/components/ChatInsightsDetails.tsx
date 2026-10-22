import type {
  ChatInsightsStatistics,
  EmojiFrequency,
  WordFrequency,
} from "../api";
import { formatNumber } from "../format";
import { sectionEyebrowClassName } from "../styles";
import { MetricCard } from "./Feedback";
import {
  buildSenderShareChart,
  type SenderShareMetric,
} from "./chatInsightsUtils";

function SenderRankings({ chat }: { chat: ChatInsightsStatistics }) {
  return (
    <section className="mt-5" aria-labelledby="sender-rankings-title">
      <h3 id="sender-rankings-title" className="mb-3 text-subheading font-bold text-ink">
        Popular words and emojis by sender
      </h3>
      <div className="grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        {chat.senders.map((sender) => (
          <article
            className="rounded-lg border border-border-subtle bg-surface p-4"
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
              <section className="rounded-lg border border-border-subtle bg-surface p-4">
                <h5 className="mb-3 text-ui font-semibold text-ink">Top words</h5>
                {sender.popular_words.length > 0 ? (
                  <RankingChips
                    items={sender.popular_words}
                    getLabel={(item) => item.word}
                    countLabel="uses"
                    labelClassName="font-semibold text-ink"
                    countClassName="text-caption font-medium text-ink-muted"
                  />
                ) : (
                  <p className="m-0 text-small text-ink-muted">
                    No words in text messages.
                  </p>
                )}
              </section>
              <section className="rounded-lg border border-border-subtle bg-surface p-4">
                <h5 className="mb-3 text-ui font-semibold text-ink">Top emojis</h5>
                {sender.popular_emojis.length > 0 ? (
                  <RankingChips
                    items={sender.popular_emojis}
                    getLabel={(item) => item.emoji}
                    countLabel="uses"
                    labelClassName="text-base"
                    countClassName="text-caption font-medium text-ink-muted"
                  />
                ) : (
                  <p className="m-0 text-small text-ink-muted">
                    No emojis in text messages.
                  </p>
                )}
              </section>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function RankingChips<T extends WordFrequency | EmojiFrequency>({
  items,
  getLabel,
  countLabel,
  labelClassName = "",
  countClassName = "",
}: {
  items: T[];
  getLabel: (item: T) => string;
  countLabel: string;
  labelClassName?: string;
  countClassName?: string;
}) {
  return (
    <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
      {items.map((item) => {
        const label = getLabel(item);
        return (
          <li
            className="inline-flex items-baseline gap-1.5 whitespace-nowrap rounded bg-surface-muted px-2 py-1"
            key={label}
            aria-label={`${label}, ${formatNumber(item.count)} ${countLabel}`}
          >
            <span className={labelClassName}>{label}</span>
            <span className={countClassName}>{formatNumber(item.count)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function ReactionAnalytics({ chat }: { chat: ChatInsightsStatistics }) {
  return (
    <section className="mt-6" aria-labelledby="reaction-analytics-title">
      <div className="mb-3">
        <p className={sectionEyebrowClassName}>REACTIONS</p>
        <h3
          id="reaction-analytics-title"
          className="m-0 text-subheading font-bold text-ink"
        >
          Reaction patterns
        </h3>
      </div>
      <p className="mb-4 rounded-lg border border-border-brand bg-surface-green px-4 py-3 text-small leading-[1.5] text-ink-green">
        Chat-wide emoji totals use the full reaction counts in the export.
        Per-person counts and reactor-to-author percentages use Telegram’s
        “recent” reactor lists only, so they show observed coverage and are
        lower bounds when those lists are incomplete.
      </p>
      <section className="rounded-lg border border-border-subtle bg-surface p-4">
        <h4 className="mb-3 text-ui font-semibold text-ink">
          Most popular reactions · {formatNumber(chat.reaction_count)} total
        </h4>
        {chat.reaction_emojis.length > 0 ? (
          <RankingChips
            items={chat.reaction_emojis}
            getLabel={(item) => item.emoji}
            countLabel="reactions"
          />
        ) : (
          <p className="m-0 text-small text-ink-muted">
            No exported emoji reactions in this chat.
          </p>
        )}
      </section>
      <div className="mt-3 grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        <section className="rounded-lg border border-border-subtle bg-surface p-4">
          <h4 className="mb-3 text-ui font-semibold text-ink">Observed reactions by person</h4>
          {chat.reactors.length === 0 ? (
            <p className="m-0 text-small text-ink-muted">
              No identified reactors in the exported recent lists.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-small">
                <thead>
                  <tr className="border-b border-border-subtle text-caption text-ink-muted">
                    <th className="py-2 pr-3 font-semibold">Person</th>
                    <th className="py-2 pr-3 font-semibold">Observed reactions</th>
                    <th className="py-2 font-semibold">Top reactions</th>
                  </tr>
                </thead>
                <tbody>
                  {chat.reactors.map((reactor) => (
                    <tr
                      className="border-b border-border-subtle last:border-b-0"
                      key={reactor.reactor_telegram_id}
                    >
                      <td className="py-2 pr-3 text-ink">{reactor.display_name}</td>
                      <td className="py-2 pr-3 text-ink">
                        {formatNumber(reactor.reaction_count)}
                      </td>
                      <td className="py-2 text-ink">
                        {reactor.popular_emojis.length > 0 ? (
                          <RankingChips
                            items={reactor.popular_emojis}
                            getLabel={(item) => item.emoji}
                            countLabel="observed reactions"
                          />
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <section className="rounded-lg border border-border-subtle bg-surface p-4">
          <h4 className="mb-3 text-ui font-semibold text-ink">
            Who reacts to whose messages
          </h4>
          {chat.reactor_author_pairs.length === 0 ? (
            <p className="m-0 text-small text-ink-muted">
              No identified reactor-to-author pairs in the exported recent lists.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-small">
                <thead>
                  <tr className="border-b border-border-subtle text-caption text-ink-muted">
                    <th className="py-2 pr-3 font-semibold">Reactor → author</th>
                    <th className="py-2 pr-3 font-semibold">Messages observed</th>
                    <th className="py-2 font-semibold">Observed share</th>
                  </tr>
                </thead>
                <tbody>
                  {chat.reactor_author_pairs.map((pair) => (
                    <tr
                      className="border-b border-border-subtle last:border-b-0"
                      key={`${pair.reactor_telegram_id}:${pair.author_telegram_id}`}
                    >
                      <td className="py-2 pr-3 text-ink">
                        {pair.reactor_name} → {pair.author_name}
                      </td>
                      <td className="py-2 pr-3 text-ink">
                        {formatNumber(pair.messages_with_observed_reaction_count)} /{" "}
                        {formatNumber(pair.author_message_count)}
                      </td>
                      <td className="py-2 text-ink">
                        {pair.observed_message_percentage.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

function SenderShareChart({
  title,
  senders,
  total,
  metric,
}: {
  title: string;
  senders: ChatInsightsStatistics["senders"];
  total: number;
  metric: SenderShareMetric;
}) {
  const { slices, pieBackground, chartDescription } = buildSenderShareChart(
    senders,
    total,
    metric,
  );

  return (
    <section
      className="rounded-lg border border-border-subtle bg-surface p-4"
      aria-label={title}
    >
      <h3 className="mb-4 text-ui font-semibold text-ink">
        {title} (top 10 senders)
      </h3>
      {senders.length === 0 ? (
        <p className="m-0 text-small text-ink-muted">No sender data available.</p>
      ) : (
        <div className="flex flex-wrap items-center gap-5">
          <div
            className="size-36 shrink-0 rounded-full"
            style={{ background: pieBackground }}
            role="img"
            aria-label={`${title}: ${chartDescription || "0%"}`}
          />
          <ul className="m-0 min-w-0 list-none space-y-2 p-0">
            {slices.map(({ key, label, value, percentage, color }) => (
              <li className="flex items-center gap-2 text-small" key={key}>
                <span
                  className="size-3 shrink-0 rounded-sm"
                  style={{ backgroundColor: color }}
                  aria-hidden="true"
                />
                <span className="min-w-0 truncate font-semibold text-ink">
                  {label}
                </span>
                <span className="shrink-0 text-caption text-ink-muted">
                  {formatNumber(value)} {metric} · {percentage.toFixed(1)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function ChatInsightsDetails({ chat }: { chat: ChatInsightsStatistics }) {
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
      <div className="grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        <section className="rounded-lg border border-border-subtle bg-surface p-4">
          <h3 className="mb-3 text-ui font-semibold text-ink">
            Most popular words
          </h3>
          {chat.popular_words.length > 0 ? (
            <RankingChips
              items={chat.popular_words}
              getLabel={(item) => item.word}
              countLabel="uses"
              labelClassName="font-semibold text-ink"
              countClassName="text-caption font-medium text-ink-muted"
            />
          ) : (
            <p className="m-0 text-small text-ink-muted">
              No words in text messages.
            </p>
          )}
        </section>
        <section className="rounded-lg border border-border-subtle bg-surface p-4">
          <h3 className="mb-3 text-ui font-semibold text-ink">
            Most popular emojis in text
          </h3>
          {chat.popular_emojis.length > 0 ? (
            <RankingChips
              items={chat.popular_emojis}
              getLabel={(item) => item.emoji}
              countLabel="uses"
            />
          ) : (
            <p className="m-0 text-small text-ink-muted">
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
