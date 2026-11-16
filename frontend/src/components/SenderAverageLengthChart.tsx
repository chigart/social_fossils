import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../utils/format";
import {
  chatInsightsCardClassName,
  chatInsightsEmptyTextClassName,
} from "../constants";
import { buildSenderAverageLengthChart } from "../utils/chatInsights";
import { TimelineChart } from "./TimelineChart";

function formatAverage(value: number) {
  return formatNumber(Math.round(value * 10) / 10);
}

export function SenderAverageLengthChart({
  senders,
}: {
  senders: ChatInsightsStatistics["senders"];
}) {
  const { senders: rankedSenders } = buildSenderAverageLengthChart(senders);

  return (
    <>
      <section
        className={chatInsightsCardClassName}
        aria-label="Average message length by person"
      >
        <h3 className="mb-2 text-ui font-semibold text-ink">
          Average message length by person (all senders)
        </h3>
        <p className="mb-4 text-small text-ink-muted">
          Text volume divided by ordinary message count, ranked by characters
          per message. Color intensity follows average message length, matching
          the Overview heatmap.
        </p>
        {rankedSenders.length === 0 ? (
          <p className={chatInsightsEmptyTextClassName}>
            No sender data with messages available.
          </p>
        ) : (
          <TimelineChart
            points={rankedSenders.map((sender) => ({
              label: sender.label,
              count: sender.averageLength,
            }))}
            showDirection={false}
            title="Average message length by person"
            description="Average text characters per ordinary message by sender. The chart can be scrolled horizontally. Bar color intensity follows average message length, matching the Overview heatmap."
            chartId="sender-average-length-chart"
            heatmap
            barWidthRatio={0.705}
            maxBarWidth={62}
            fixedSlotWidth={88}
            labelFontSize={13.5}
            formatTick={formatAverage}
          />
        )}
        {rankedSenders.length > 0 && (
          <ul className="sr-only" aria-label="Average message length details">
            {rankedSenders.map((sender) => (
              <li key={sender.key}>
                {sender.label}: {formatAverage(sender.averageLength)} characters
                per message ({formatNumber(sender.textLength)} characters across{" "}
                {formatNumber(sender.messageCount)} messages)
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
