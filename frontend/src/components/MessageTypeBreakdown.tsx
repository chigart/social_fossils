import type { ChatInsightsStatistics, MessageTypeCount } from "../api";
import { formatNumber } from "../utils/format";
import {
  chatInsightsCardClassName,
  chatInsightsDescriptionClassName,
  chatInsightsEmptyTextClassName,
  chatInsightsSectionClassName,
  chatInsightsSectionHeaderClassName,
  chatInsightsSubheadingClassName,
  sectionEyebrowClassName,
} from "../constants";
import {
  PERCENTAGE_DECIMAL_PLACES,
  TOP_MESSAGE_TYPE_SENDER_COUNT,
} from "../constants";
import { buildMessageTypeShareChart } from "../utils/chatInsights";

function MessageTypeChart({ item }: { item: MessageTypeCount }) {
  const { slices, pieBackground, chartDescription } =
    buildMessageTypeShareChart(item.senders);

  return (
    <article className={chatInsightsCardClassName}>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="m-0 text-ui font-semibold text-ink">{item.category}</h4>
        <span className="text-caption text-ink-muted">
          {formatNumber(item.count)} messages
        </span>
      </div>
      <p className="mb-4 mt-0 text-caption text-ink-muted">
        {formatNumber(item.with_text_count)} with text
      </p>
      {slices.length === 0 ? (
        <p className={chatInsightsEmptyTextClassName}>
          No sender data available.
        </p>
      ) : (
        <div className="flex flex-wrap items-center gap-4">
          <div
            className="size-28 shrink-0 rounded-full"
            style={{ background: pieBackground }}
            role="img"
            aria-label={`${item.category} sender share: ${chartDescription}`}
          />
          <ul className="m-0 min-w-0 list-none space-y-2 p-0">
            {slices.map((slice) => (
              <li
                className="flex min-w-0 items-center gap-2 text-small"
                key={slice.key}
                aria-label={`${slice.label}, ${formatNumber(slice.value)} messages, ${slice.percentage.toFixed(PERCENTAGE_DECIMAL_PLACES)}%`}
              >
                <span
                  className="size-3 shrink-0 rounded-sm"
                  style={{ backgroundColor: slice.color }}
                  aria-hidden="true"
                />
                <span className="min-w-0 truncate font-semibold text-ink">
                  {slice.label}
                </span>
                <span className="shrink-0 text-caption text-ink-muted">
                  {formatNumber(slice.value)} ·{" "}
                  {slice.percentage.toFixed(PERCENTAGE_DECIMAL_PLACES)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

export function MessageTypeBreakdown({
  chat,
}: {
  chat: ChatInsightsStatistics;
}) {
  const breakdown = chat.message_type_breakdown
    .filter(
      (item) =>
        item.category.toLowerCase() !== "text" &&
        item.category.toLowerCase() !== "unclassified",
    )
    .sort(
      (first, second) =>
        second.count - first.count ||
        first.category.localeCompare(second.category),
    );

  return (
    <section
      className={`${chatInsightsSectionClassName} mb-6`}
      aria-labelledby="message-type-breakdown-title"
    >
      <div className={chatInsightsSectionHeaderClassName}>
        <p className={sectionEyebrowClassName}>MEDIA & EVENTS</p>
        <h3
          id="message-type-breakdown-title"
          className={chatInsightsSubheadingClassName}
        >
          Message type breakdown
        </h3>
      </div>
      <p className={chatInsightsDescriptionClassName}>
        Each exported message is counted once by its primary type. Captions
        remain attached to their media category; service events remain separate
        from ordinary messages. Each category has its own pie chart, using its
        top {TOP_MESSAGE_TYPE_SENDER_COUNT} senders normalized to 100%.
      </p>
      {breakdown.length === 0 ? (
        <p className={chatInsightsEmptyTextClassName}>
          No message type information is available.
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-3 max-[1000px]:grid-cols-2 max-sm:grid-cols-1">
          {breakdown.map((item) => (
            <MessageTypeChart item={item} key={item.category} />
          ))}
        </div>
      )}
    </section>
  );
}
