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
  filterRepeatedItems,
  type SenderShareMetric,
} from "./chatInsightsUtils";

function SenderRankings({ chat }: { chat: ChatInsightsStatistics }) {
  return (
    <section className="mt-5" aria-labelledby="sender-rankings-title">
      <h3 id="sender-rankings-title" className="mb-3 text-subheading font-bold text-ink">
        Popular words and emojis by sender
      </h3>
      <div className="grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        {chat.senders.map((sender) => {
          const popularWords = filterRepeatedItems(sender.popular_words);
          const popularEmojis = filterRepeatedItems(sender.popular_emojis);
          return (
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
                  {popularWords.length > 0 ? (
                    <RankingChips
                      items={popularWords}
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
                  {popularEmojis.length > 0 ? (
                    <RankingChips
                      items={popularEmojis}
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
          );
        })}
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

function formatResponseTime(seconds: number | null) {
  if (seconds === null) return "Not available";
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} hr`;
  return `${(seconds / 86400).toFixed(1)} days`;
}

function ConversationFlow({ chat }: { chat: ChatInsightsStatistics }) {
  const activity = chat.conversation_activity;
  const replyTempo = chat.reply_tempo;
  const senderGroups = [
    { title: "Conversation openers", senders: activity.opening_senders },
    { title: "Conversation closers", senders: activity.closing_senders },
  ];

  return (
    <section className="mt-6" aria-labelledby="conversation-flow-title">
      <div className="mb-3">
        <p className={sectionEyebrowClassName}>REPLY TEMPO & TURN-TAKING</p>
        <h3
          id="conversation-flow-title"
          className="m-0 text-subheading font-bold text-ink"
        >
          Conversation flow
        </h3>
      </div>
      <p className="mb-4 text-small leading-[1.5] text-ink-muted">
        A conversation starts after {activity.session_gap_hours} hours without
        an ordinary message. Reply times include only matched, dated replies
        between identified senders; unknown senders and missing timestamps are
        excluded.
      </p>
      <div className="mb-4 grid grid-cols-4 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
        <MetricCard
          label="Conversations"
          value={formatNumber(activity.session_count)}
          detail={`${formatNumber(activity.messages_without_timestamp_count)} undated messages excluded`}
        />
        <MetricCard
          label="Median reply time"
          value={formatResponseTime(replyTempo.median_response_seconds)}
          detail={`${formatNumber(replyTempo.measured_reply_count)} measured of ${formatNumber(replyTempo.reply_reference_count)} reply references`}
        />
        <MetricCard
          label="Turn-taking"
          value={`${activity.sender_switch_percentage.toFixed(1)}%`}
          detail={`${formatNumber(activity.sender_switch_count)} sender switches of ${formatNumber(activity.sender_transition_count)} identified transitions`}
        />
        <MetricCard
          label="Longest turn-taking streak"
          value={formatNumber(activity.longest_turn_taking_streak)}
          detail="messages with a sender switch each turn"
        />
      </div>
      <div className="grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        {senderGroups.map(({ title, senders }) => (
          <section
            className="rounded-lg border border-border-subtle bg-surface p-4"
            key={title}
          >
            <h4 className="mb-3 text-ui font-semibold text-ink">{title}</h4>
            {senders.length === 0 ? (
              <p className="m-0 text-small text-ink-muted">
                No dated conversations available.
              </p>
            ) : (
              <ul className="m-0 list-none space-y-2 p-0">
                {senders.map((sender) => (
                  <li
                    className="flex justify-between gap-3 text-small"
                    key={sender.sender_telegram_id ?? "unknown"}
                  >
                    <span className="truncate text-ink">{sender.display_name}</span>
                    <span className="shrink-0 text-ink-muted">
                      {formatNumber(sender.count)} conversations
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
      <section
        className="mt-3 rounded-lg border border-border-subtle bg-surface p-4"
        aria-labelledby="conversation-handoffs-title"
      >
        <h4
          id="conversation-handoffs-title"
          className="mb-3 text-ui font-semibold text-ink"
        >
          Who reopens after a pause
        </h4>
        <p className="mb-3 text-caption text-ink-muted">
          Previous conversation closer → next conversation opener ·{" "}
          {formatNumber(activity.unattributed_handoff_count)} transitions have
          an unknown participant.
        </p>
        {activity.handoffs.length === 0 ? (
          <p className="m-0 text-small text-ink-muted">
            No fully attributed conversation handoffs available.
          </p>
        ) : (
          <ul className="m-0 list-none space-y-2 p-0">
            {activity.handoffs.map((handoff) => (
              <li
                className="flex justify-between gap-3 text-small"
                key={`${handoff.previous_closer_id}:${handoff.next_opener_id}`}
              >
                <span className="truncate text-ink">
                  {handoff.previous_closer_name} → {handoff.next_opener_name}
                </span>
                <span className="shrink-0 text-ink-muted">
                  {formatNumber(handoff.count)} times
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

function MessageTypeBreakdown({ chat }: { chat: ChatInsightsStatistics }) {
  return (
    <section className="mt-6" aria-labelledby="message-type-breakdown-title">
      <div className="mb-3">
        <p className={sectionEyebrowClassName}>TEXT, MEDIA & EVENTS</p>
        <h3
          id="message-type-breakdown-title"
          className="m-0 text-subheading font-bold text-ink"
        >
          Message type breakdown
        </h3>
      </div>
      <p className="mb-4 text-small leading-[1.5] text-ink-muted">
        Each exported message is counted once by its primary type. Captions
        remain attached to their media category; service events and unclassified
        messages are shown separately.
      </p>
      {chat.message_type_breakdown.length === 0 ? (
        <p className="m-0 text-small text-ink-muted">
          No message type information is available.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border-subtle bg-surface">
          <table className="w-full border-collapse text-left text-small">
            <thead>
              <tr className="border-b border-border-subtle text-caption text-ink-muted">
                <th className="px-4 py-2 font-semibold">Message type</th>
                <th className="px-4 py-2 font-semibold">Messages</th>
                <th className="px-4 py-2 font-semibold">With text</th>
              </tr>
            </thead>
            <tbody>
              {chat.message_type_breakdown.map((item) => (
                <tr
                  className="border-b border-border-subtle last:border-b-0"
                  key={item.category}
                >
                  <th scope="row" className="px-4 py-2 font-medium text-ink">
                    {item.category}
                  </th>
                  <td className="px-4 py-2 text-ink">
                    {formatNumber(item.count)}
                  </td>
                  <td className="px-4 py-2 text-ink">
                    {formatNumber(item.with_text_count)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

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
      <ConversationFlow chat={chat} />
      <MessageTypeBreakdown chat={chat} />
      <div className="grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        <section className="rounded-lg border border-border-subtle bg-surface p-4">
          <h3 className="mb-3 text-ui font-semibold text-ink">
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
            <p className="m-0 text-small text-ink-muted">
              No words in text messages.
            </p>
          )}
        </section>
        <section className="rounded-lg border border-border-subtle bg-surface p-4">
          <h3 className="mb-3 text-ui font-semibold text-ink">
            Most popular emojis in text
          </h3>
          {popularEmojis.length > 0 ? (
            <RankingChips
              items={popularEmojis}
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
