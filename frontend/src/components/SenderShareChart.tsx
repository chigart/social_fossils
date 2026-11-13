import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../utils/format";
import { chatInsightsCardClassName, chatInsightsEmptyTextClassName } from "../constants";
import {
  PERCENTAGE_DECIMAL_PLACES,
  TOP_SENDER_COUNT,
} from "../constants";
import { buildSenderShareChart, type SenderShareMetric } from "../utils/chatInsights";

export function SenderShareChart({
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
    <section className={chatInsightsCardClassName} aria-label={title}>
      <h3 className="mb-4 text-ui font-semibold text-ink">
        {title} (top {TOP_SENDER_COUNT} senders)
      </h3>
      {senders.length === 0 ? (
        <p className={chatInsightsEmptyTextClassName}>
          No sender data available.
        </p>
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
                  {formatNumber(value)} {metric} ·{" "}
                  {percentage.toFixed(PERCENTAGE_DECIMAL_PLACES)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
