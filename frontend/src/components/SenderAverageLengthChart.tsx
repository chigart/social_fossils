import { useId } from "react";
import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../format";
import {
  chatInsightsCardClassName,
  chatInsightsEmptyTextClassName,
} from "../styles";
import { buildSenderAverageLengthChart } from "./chatInsightsUtils";

const MINIMUM_CHART_WIDTH = 620;
const CHART_HEIGHT = 240;
const CHART_TOP_PADDING = 16;
const CHART_BOTTOM_PADDING = 58;
const Y_AXIS_WIDTH = 46;
const CHART_RIGHT_PADDING = 18;
const SLOT_WIDTH = 88;
const BAR_WIDTH = 36;
const PLOT_BOTTOM = CHART_HEIGHT - CHART_BOTTOM_PADDING;
const PLOT_HEIGHT = PLOT_BOTTOM - CHART_TOP_PADDING;

function splitSenderLabel(label: string) {
  const midpoint = Math.ceil(label.length / 2);
  const breakAt = [...label.matchAll(/\s+/g)].reduce(
    (closestIndex, match) => {
      const index = match.index;
      return Math.abs(index - midpoint) <
        Math.abs(closestIndex - midpoint)
        ? index
        : closestIndex;
    },
    -1,
  );
  if (breakAt < 0 && label.length <= 12) return [label];
  const splitIndex = breakAt >= 0 ? breakAt : midpoint;

  return [
    label.slice(0, splitIndex).trim(),
    label.slice(splitIndex).trim(),
  ].filter(Boolean);
}

function formatAverage(value: number) {
  return formatNumber(Math.round(value * 10) / 10);
}

export function SenderAverageLengthChart({
  senders,
}: {
  senders: ChatInsightsStatistics["senders"];
}) {
  const chartId = useId();
  const { senders: rankedSenders, maximum } =
    buildSenderAverageLengthChart(senders);
  const chartWidth = Math.max(
    MINIMUM_CHART_WIDTH,
    Y_AXIS_WIDTH +
      rankedSenders.length * SLOT_WIDTH +
      CHART_RIGHT_PADDING,
  );
  const safeMaximum = maximum || 1;
  const titleId = `${chartId}-title`;
  const descriptionId = `${chartId}-description`;

  return (
    <section
      className={chatInsightsCardClassName}
      aria-label="Average message length by person"
    >
      <h3 className="mb-2 text-ui font-semibold text-ink">
        Average message length by person (all senders)
      </h3>
      <p className="mb-4 text-small text-ink-muted">
        Text volume divided by ordinary message count, ranked by characters per
        message.
      </p>
      {rankedSenders.length === 0 ? (
        <p className={chatInsightsEmptyTextClassName}>
          No sender data with messages available.
        </p>
      ) : (
        <>
          <div className="w-full overflow-x-auto rounded-lg border border-border-subtle bg-surface-subtle p-3">
            <svg
              className="block h-auto"
              style={{ minWidth: `${chartWidth}px` }}
              width="100%"
              height={CHART_HEIGHT}
              viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`}
              role="img"
              aria-labelledby={titleId}
              aria-describedby={descriptionId}
            >
              <title id={titleId}>Average message length by person</title>
              <desc id={descriptionId}>
                All senders ranked by average text characters per ordinary
                message. Each sender has a vertical bar, and the chart can be
                scrolled horizontally.
              </desc>
              {[0, 0.5, 1].map((fraction) => {
                const y = PLOT_BOTTOM - PLOT_HEIGHT * fraction;
                return (
                  <g key={fraction}>
                    <line
                      x1={Y_AXIS_WIDTH}
                      x2={chartWidth - CHART_RIGHT_PADDING}
                      y1={y}
                      y2={y}
                      stroke="var(--color-border)"
                      strokeWidth="1"
                    />
                    <text
                      x={Y_AXIS_WIDTH - 7}
                      y={y + 3}
                      textAnchor="end"
                      fill="var(--color-ink-muted)"
                      fontSize="9"
                    >
                      {formatAverage(maximum * fraction)}
                    </text>
                  </g>
                );
              })}
              {rankedSenders.map((sender, index) => {
                const slotStart = Y_AXIS_WIDTH + index * SLOT_WIDTH;
                const barHeight =
                  (sender.averageLength / safeMaximum) * PLOT_HEIGHT;
                return (
                  <g
                    key={sender.key}
                    aria-label={`${sender.label}: ${formatAverage(sender.averageLength)} characters per message`}
                  >
                    <text
                      x={slotStart + SLOT_WIDTH / 2}
                      y={PLOT_BOTTOM + 17}
                      textAnchor="middle"
                      fill="var(--color-ink)"
                      fontSize="10"
                      data-sender-name={sender.label}
                    >
                      {splitSenderLabel(sender.label).map((line, lineIndex) => (
                        <tspan
                          key={`${sender.key}-${lineIndex}`}
                          x={slotStart + SLOT_WIDTH / 2}
                          dy={lineIndex === 0 ? 0 : 12}
                        >
                          {line}
                        </tspan>
                      ))}
                    </text>
                    <rect
                      x={slotStart + (SLOT_WIDTH - BAR_WIDTH) / 2}
                      y={PLOT_BOTTOM - barHeight}
                      width={BAR_WIDTH}
                      height={barHeight}
                      rx="4"
                      fill="var(--color-brand-strong)"
                      data-sender={sender.label}
                      data-average-length={sender.averageLength}
                    />
                  </g>
                );
              })}
            </svg>
          </div>
          <ul className="sr-only" aria-label="Average message length details">
            {rankedSenders.map((sender) => (
              <li key={sender.key}>
                {sender.label}: {formatAverage(sender.averageLength)} characters
                per message ({formatNumber(sender.textLength)} characters across{" "}
                {formatNumber(sender.messageCount)} messages)
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
