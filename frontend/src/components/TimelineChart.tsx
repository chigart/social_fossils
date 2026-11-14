import { formatNumber } from "../utils/format";

export type TimelinePoint = {
  label: string;
  count: number;
  ownerCount?: number;
  contactCount?: number;
  unknownCount?: number;
  lineValue?: number;
};

export function TimelineChart({
  points,
  showDirection,
  title,
  description,
  chartId,
  compareOwnerCount = false,
  lineLegendLabel,
}: {
  points: TimelinePoint[];
  showDirection: boolean;
  title: string;
  description: string;
  chartId: string;
  compareOwnerCount?: boolean;
  lineLegendLabel?: string;
}) {
  const width = Math.max(620, points.length * 50);
  const height = 240;
  const plotTop = 15;
  const plotBottom = 180;
  const plotHeight = plotBottom - plotTop;
  const plotLeft = 48;
  const plotRight = width - 8;
  const plotWidth = plotRight - plotLeft;
  const slotWidth = plotWidth / points.length;
  const barWidth = Math.min(30, slotWidth * 0.66);
  const comparisonBarWidth = Math.min(20, slotWidth * 0.28);
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
      x: plotLeft + (points.indexOf(point) + 0.5) * slotWidth,
      y: plotBottom - ((point.lineValue ?? 0) / lineMaximum) * plotHeight,
    }));
  const chartTitleId = `${chartId}-title`;
  const chartDescriptionId = `${chartId}-description`;

  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border-subtle bg-surface-subtle p-3">
      <svg
        className="block h-auto"
        style={{ minWidth: `${width}px` }}
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-labelledby={chartTitleId}
        aria-describedby={chartDescriptionId}
      >
        <title id={chartTitleId}>{title}</title>
        <desc id={chartDescriptionId}>{description}</desc>
        {[0, 0.5, 1].map((fraction) => {
          const y = plotBottom - plotHeight * fraction;
          const count = Math.round(maximum * fraction);
          return (
            <g key={fraction}>
              <line
                x1={plotLeft}
                x2={plotRight}
                y1={y}
                y2={y}
                stroke="var(--color-border)"
                strokeWidth="1"
              />
              <text
                x={36}
                y={y + 3}
                textAnchor="end"
                fill="var(--color-ink-muted)"
                fontSize="10"
              >
                {count}
              </text>
            </g>
          );
        })}
        {points.map((point, index) => {
          const centerX = plotLeft + (index + 0.5) * slotWidth;
          const x = centerX - barWidth / 2;
          const owner = showDirection ? (point.ownerCount ?? 0) : 0;
          const contact = showDirection ? (point.contactCount ?? 0) : 0;
          const unknown = point.unknownCount ?? point.count;
          const ownerHeight = (owner / maximum) * plotHeight;
          const contactHeight = (contact / maximum) * plotHeight;
          const unknownHeight = (unknown / maximum) * plotHeight;
          const totalHeight = (point.count / maximum) * plotHeight;
          const ownerSeriesHeight =
            ((point.ownerCount ?? 0) / maximum) * plotHeight;
          const zeroHeight = point.count === 0 ? 2 : 0;
          return (
            <g key={point.label}>
              <rect
                x={x}
                y={plotBottom - totalHeight - zeroHeight}
                width={barWidth}
                height={totalHeight + zeroHeight}
                fill="var(--color-clear)"
                data-month={point.label}
                data-count={point.count}
                aria-label={`${point.label}: ${formatNumber(point.count)}`}
              />
              {compareOwnerCount && point.ownerCount !== undefined ? (
                <>
                  <rect
                    x={centerX - comparisonBarWidth - 2}
                    y={plotBottom - totalHeight}
                    width={comparisonBarWidth}
                    height={totalHeight}
                    fill="var(--color-timeline-contact)"
                    data-year={point.label}
                    data-year-total-count={point.count}
                  />
                  <rect
                    x={centerX + 2}
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
                  strokeWidth="2"
                  strokeDasharray="2 2"
                />
              )}
              <text
                x={centerX}
                y={plotBottom + 17}
                textAnchor="middle"
                fill="var(--color-ink-subtle)"
                fontSize="9"
              >
                {point.label}
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
                strokeWidth="2.5"
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
                r="4"
                fill="var(--color-timeline-contact)"
                stroke="var(--color-surface)"
                strokeWidth="1.5"
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
