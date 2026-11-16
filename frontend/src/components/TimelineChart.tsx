import { formatNumber } from "../utils/format";
import { heatmapColor } from "../utils/heatmap";
import {
  CHART_HEIGHT,
  CHART_RIGHT_PADDING,
  CHART_TOP_PADDING,
  MINIMUM_CHART_WIDTH,
  PLOT_BOTTOM,
  PLOT_HEIGHT,
  TIMELINE_COMPARISON_BAR_GAP,
  TIMELINE_COMPARISON_BAR_WIDTH,
  TIMELINE_COMPARISON_BAR_WIDTH_RATIO,
  TIMELINE_DEFAULT_BAR_WIDTH_RATIO,
  TIMELINE_DEFAULT_MAX_BAR_WIDTH,
  TIMELINE_DEFAULT_SLOT_WIDTH,
  TIMELINE_FIXED_SLOT_WIDTH_PADDING,
  TIMELINE_GRID_FRACTIONS,
  TIMELINE_GRID_STROKE_WIDTH,
  TIMELINE_LABEL_BASELINE_OFFSET,
  TIMELINE_LABEL_FONT_SIZE,
  TIMELINE_LABEL_LINE_HEIGHT,
  TIMELINE_LABEL_WRAP_THRESHOLD,
  TIMELINE_LINE_POINT_RADIUS,
  TIMELINE_LINE_POINT_STROKE_WIDTH,
  TIMELINE_LINE_STROKE_WIDTH,
  TIMELINE_TICK_LABEL_FONT_SIZE,
  TIMELINE_TICK_LABEL_X,
  TIMELINE_TICK_LABEL_Y_OFFSET,
  TIMELINE_ZERO_BAR_HEIGHT,
  TIMELINE_ZERO_MARKER_DASH_PATTERN,
  TIMELINE_ZERO_MARKER_STROKE_WIDTH,
  Y_AXIS_WIDTH,
} from "../constants";

export type TimelinePoint = {
  label: string;
  displayLabel?: string;
  count: number;
  ownerCount?: number;
  contactCount?: number;
  unknownCount?: number;
  lineValue?: number;
};

function splitLabel(label: string): string[] {
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
  if (breakAt < 0 && label.length <= TIMELINE_LABEL_WRAP_THRESHOLD) {
    return [label];
  }
  const splitIndex = breakAt >= 0 ? breakAt : midpoint;

  return [
    label.slice(0, splitIndex).trim(),
    label.slice(splitIndex).trim(),
  ].filter(Boolean);
}

export function TimelineChart({
  points,
  showDirection,
  title,
  description,
  chartId,
  compareOwnerCount = false,
  lineLegendLabel,
  heatmap = false,
  fitContainer = false,
  barWidthRatio = TIMELINE_DEFAULT_BAR_WIDTH_RATIO,
  maxBarWidth = TIMELINE_DEFAULT_MAX_BAR_WIDTH,
  fixedSlotWidth,
  labelFontSize = TIMELINE_LABEL_FONT_SIZE,
  formatTick = (value) => Math.round(value).toLocaleString(),
}: {
  points: TimelinePoint[];
  showDirection: boolean;
  title: string;
  description: string;
  chartId: string;
  compareOwnerCount?: boolean;
  lineLegendLabel?: string;
  heatmap?: boolean;
  fitContainer?: boolean;
  barWidthRatio?: number;
  maxBarWidth?: number;
  fixedSlotWidth?: number;
  labelFontSize?: number;
  formatTick?: (value: number) => string;
}) {
  const width = fitContainer
    ? MINIMUM_CHART_WIDTH
    : Math.max(
        MINIMUM_CHART_WIDTH,
        fixedSlotWidth === undefined
          ? points.length * TIMELINE_DEFAULT_SLOT_WIDTH
          : TIMELINE_FIXED_SLOT_WIDTH_PADDING + points.length * fixedSlotWidth,
      );
  const height = CHART_HEIGHT;
  const plotTop = CHART_TOP_PADDING;
  const plotBottom = PLOT_BOTTOM;
  const plotHeight = PLOT_HEIGHT;
  const plotLeft = Y_AXIS_WIDTH;
  const plotRight = width - CHART_RIGHT_PADDING;
  const plotWidth = plotRight - plotLeft;
  const slotWidth = fixedSlotWidth ?? plotWidth / Math.max(points.length, 1);
  const barWidth = Math.min(maxBarWidth, slotWidth * barWidthRatio);
  const comparisonBarWidth = Math.min(
    TIMELINE_COMPARISON_BAR_WIDTH,
    slotWidth * TIMELINE_COMPARISON_BAR_WIDTH_RATIO,
  );
  const maximum = Math.max(1, ...points.map((point) => point.count));
  const maximumLineValue = Math.max(
    0,
    ...points.map((point) => point.lineValue ?? 0),
  );
  const lineMaximum = maximumLineValue || 1;
  const linePoints = points
    .filter((point) => point.lineValue !== undefined)
    .map((point) => ({
      ...point,
      x: plotLeft + (points.indexOf(point) + 0.5) * (
        fixedSlotWidth ?? slotWidth
      ),
      y: plotBottom - ((point.lineValue ?? 0) / lineMaximum) * plotHeight,
    }));
  const chartTitleId = `${chartId}-title`;
  const chartDescriptionId = `${chartId}-description`;

  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border-subtle bg-surface-subtle p-3">
      <svg
        className="block h-auto"
        style={{ minWidth: fitContainer ? "100%" : `${width}px` }}
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-labelledby={chartTitleId}
        aria-describedby={chartDescriptionId}
      >
        <title id={chartTitleId}>{title}</title>
        <desc id={chartDescriptionId}>{description}</desc>
        {TIMELINE_GRID_FRACTIONS.map((fraction) => {
          const y = plotBottom - plotHeight * fraction;
          return (
            <g key={fraction}>
              <line
                x1={plotLeft}
                x2={plotRight}
                y1={y}
                y2={y}
                stroke="var(--color-border)"
                strokeWidth={TIMELINE_GRID_STROKE_WIDTH}
              />
              <text
                x={TIMELINE_TICK_LABEL_X}
                y={y + TIMELINE_TICK_LABEL_Y_OFFSET}
                textAnchor="end"
                fill="var(--color-ink-muted)"
                fontSize={TIMELINE_TICK_LABEL_FONT_SIZE}
              >
                {formatTick(maximum * fraction)}
              </text>
            </g>
          );
        })}
        {points.map((point, index) => {
          const centerX = plotLeft + (index + 0.5) * slotWidth;
          const x = centerX - barWidth / 2;
          const owner = showDirection ? (point.ownerCount ?? 0) : 0;
          const contact = showDirection ? (point.contactCount ?? 0) : 0;
          const unknown = heatmap ? 0 : (point.unknownCount ?? point.count);
          const ownerHeight = (owner / maximum) * plotHeight;
          const contactHeight = (contact / maximum) * plotHeight;
          const unknownHeight = (unknown / maximum) * plotHeight;
          const totalHeight = (point.count / maximum) * plotHeight;
          const ownerSeriesHeight =
            ((point.ownerCount ?? 0) / maximum) * plotHeight;
          const zeroHeight =
            point.count === 0 ? TIMELINE_ZERO_BAR_HEIGHT : 0;
          return (
            <g key={point.label}>
              <rect
                x={x}
                y={plotBottom - totalHeight - zeroHeight}
                width={barWidth}
                height={totalHeight + zeroHeight}
                fill={
                  heatmap
                    ? heatmapColor(point.count, maximum)
                    : "var(--color-clear)"
                }
                data-month={point.label}
                data-count={point.count}
                data-heatmap={
                  heatmap ? heatmapColor(point.count, maximum) : undefined
                }
                data-sender={point.label}
                data-average-length={point.count}
                aria-label={`${point.label}: ${formatNumber(point.count)}`}
              />
              {compareOwnerCount && point.ownerCount !== undefined ? (
                <>
                  <rect
                    x={
                      centerX -
                      comparisonBarWidth -
                      TIMELINE_COMPARISON_BAR_GAP
                    }
                    y={plotBottom - totalHeight}
                    width={comparisonBarWidth}
                    height={totalHeight}
                    fill="var(--color-timeline-contact)"
                    data-year={point.label}
                    data-year-total-count={point.count}
                  />
                  <rect
                    x={centerX + TIMELINE_COMPARISON_BAR_GAP}
                    y={plotBottom - ownerSeriesHeight}
                    width={comparisonBarWidth}
                    height={ownerSeriesHeight}
                    fill="var(--color-brand-strong)"
                    data-year={point.label}
                    data-year-owner-count={point.ownerCount}
                  />
                </>
              ) : (
                <>
                  {ownerHeight > 0 && (
                    <rect
                      x={x}
                      y={plotBottom - ownerHeight}
                      width={barWidth}
                      height={ownerHeight}
                      fill="var(--color-brand-strong)"
                    />
                  )}
                  {contactHeight > 0 && (
                    <rect
                      x={x}
                      y={plotBottom - ownerHeight - contactHeight}
                      width={barWidth}
                      height={contactHeight}
                      fill="var(--color-timeline-contact)"
                    />
                  )}
                  {unknownHeight > 0 && (
                    <rect
                      x={x}
                      y={plotBottom - totalHeight}
                      width={barWidth}
                      height={unknownHeight}
                      fill="var(--color-timeline-unknown)"
                    />
                  )}
                </>
              )}
              {point.count === 0 && (
                <line
                  x1={x}
                  x2={x + barWidth}
                  y1={plotBottom}
                  y2={plotBottom}
                  stroke="var(--color-timeline-unknown)"
                  strokeWidth={TIMELINE_ZERO_MARKER_STROKE_WIDTH}
                  strokeDasharray={TIMELINE_ZERO_MARKER_DASH_PATTERN}
                />
              )}
              <text
                x={centerX}
                y={plotBottom + TIMELINE_LABEL_BASELINE_OFFSET}
                textAnchor="middle"
                fill="var(--color-ink-subtle)"
                fontSize={labelFontSize}
                data-sender-name={point.label}
              >
                {splitLabel(point.displayLabel ?? point.label).map(
                  (line, lineIndex) => (
                    <tspan
                      key={`${point.label}-${lineIndex}`}
                      x={centerX}
                      dy={
                        lineIndex === 0 ? 0 : TIMELINE_LABEL_LINE_HEIGHT
                      }
                    >
                      {line}
                    </tspan>
                  ),
                )}
              </text>
            </g>
          );
        })}
        {linePoints.length > 0 && (
          <g aria-label={lineLegendLabel}>
            {linePoints.length > 1 && (
              <polyline
                points={linePoints.map(({ x, y }) => `${x},${y}`).join(" ")}
                fill="none"
                stroke="var(--color-timeline-contact)"
                strokeWidth={TIMELINE_LINE_STROKE_WIDTH}
                strokeLinejoin="round"
                strokeLinecap="round"
                data-series="average-message-size"
              />
            )}
            {linePoints.map(({ label, lineValue, x, y }) => (
              <circle
                key={label}
                cx={x}
                cy={y}
                r={TIMELINE_LINE_POINT_RADIUS}
                fill="var(--color-timeline-contact)"
                stroke="var(--color-surface)"
                strokeWidth={TIMELINE_LINE_POINT_STROKE_WIDTH}
                data-year={label}
                data-average-size={lineValue}
                aria-label={`${label}: ${formatNumber(lineValue ?? 0)} characters per message`}
              />
            ))}
          </g>
        )}
      </svg>
    </div>
  );
}
