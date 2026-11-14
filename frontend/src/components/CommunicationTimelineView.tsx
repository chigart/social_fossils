import type {
  ChatInsightSender,
  CommunicationTimelineMonth,
  CommunicationTimelineStatistics,
} from "../api";
import { formatNumber } from "../utils/format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  screenReaderOnlyClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../constants";
import type { Resource } from "../types";
import { LoadingMessage, SectionError } from "./Feedback";

function formatMonth(month: string) {
  const date = new Date(`${month}-01T00:00:00Z`);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function monthDescription(month: CommunicationTimelineMonth) {
  return [
    `${formatMonth(month.month)}: ${formatNumber(month.ordinary_message_count)} ordinary messages`,
    `${formatNumber(month.owner_message_count)} from owner`,
    `${formatNumber(month.contact_message_count)} from contact`,
    `${formatNumber(month.unknown_direction_message_count)} with unknown direction`,
    `${formatNumber(month.active_days)} active days`,
  ].join(", ");
}

function TimelineChart({
  months,
  showDirection,
}: {
  months: CommunicationTimelineMonth[];
  showDirection: boolean;
}) {
  const width = Math.max(620, months.length * 50);
  const height = 240;
  const plotTop = 15;
  const plotBottom = 180;
  const plotHeight = plotBottom - plotTop;
  const gridLineStartX = 42;
  const yAxisLabelX = 36;
  const plotWidth = width - 36;
  const slotWidth = plotWidth / months.length;
  const barWidth = Math.min(30, slotWidth * 0.66);
  const maximum = Math.max(
    1,
    ...months.map((month) => month.ordinary_message_count),
  );
  const chartTitleId = "timeline-chart-title";
  const chartDescriptionId = "timeline-chart-description";

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
        <title id={chartTitleId}>Monthly ordinary message activity</title>
        <desc id={chartDescriptionId}>
          Each stacked bar shows monthly ordinary messages. Direction is
          separated only for messages with reliable sender identity. Empty
          months remain visible between active months.
        </desc>
        {[0, 0.5, 1].map((fraction) => {
          const y = plotBottom - plotHeight * fraction;
          const count = Math.round(maximum * fraction);
          return (
            <g key={fraction}>
              <line
                x1={gridLineStartX}
                x2={plotWidth}
                y1={y}
                y2={y}
                stroke="var(--color-border)"
                strokeWidth="1"
              />
              <text
                x={yAxisLabelX}
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
        {months.map((month, index) => {
          const x = index * slotWidth + (slotWidth - barWidth) / 2;
          const owner = showDirection ? month.owner_message_count : 0;
          const contact = showDirection ? month.contact_message_count : 0;
          const unknown = month.unknown_direction_message_count;
          const ownerHeight = (owner / maximum) * plotHeight;
          const contactHeight = (contact / maximum) * plotHeight;
          const unknownHeight = (unknown / maximum) * plotHeight;
          const totalHeight = (month.ordinary_message_count / maximum) * plotHeight;
          const zeroHeight = month.ordinary_message_count === 0 ? 2 : 0;
          return (
            <g key={month.month} aria-label={monthDescription(month)}>
              <rect
                x={x}
                y={plotBottom - totalHeight - zeroHeight}
                width={barWidth}
                height={totalHeight + zeroHeight}
                fill="var(--color-clear)"
                data-month={month.month}
                data-count={month.ordinary_message_count}
                aria-label={monthDescription(month)}
              />
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
              {month.ordinary_message_count === 0 && (
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
                x={index * slotWidth + slotWidth / 2}
                y={plotBottom + 17}
                textAnchor="middle"
                fill="var(--color-ink-subtle)"
                fontSize="9"
              >
                {month.month}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function CommunicationTimelineView({
  timeline,
  onRetry,
  senders,
  selectedSenderId,
  onSenderChange,
  showSenderSelector,
}: {
  timeline: Resource<CommunicationTimelineStatistics>;
  onRetry: () => void;
  senders: ChatInsightSender[];
  selectedSenderId: string | null;
  onSenderChange: (senderId: string | null) => void;
  showSenderSelector: boolean;
}) {
  const data = timeline.data;
  const months = data?.months ?? [];
  const showDirection = months.some(
    (month) => month.owner_message_count + month.contact_message_count > 0,
  );
  const showUnknown = months.some(
    (month) => month.unknown_direction_message_count > 0,
  );
  return (
    <section
      id="communication-timeline"
      className={sectionClassName}
      aria-labelledby="communication-timeline-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>MONTHLY ACTIVITY</p>
          <h2
            id="communication-timeline-title"
            className={sectionTitleClassName}
          >
            Communication timeline
          </h2>
        </div>
        {showSenderSelector &&
          senders.some((sender) => sender.sender_id !== null) && (
            <label className="flex items-center gap-2 text-small text-ink-muted">
              Timeline user
              <select
                aria-label="Timeline user"
                className="rounded-md border border-border-subtle bg-surface px-3 py-2 text-ink"
                value={selectedSenderId ?? ""}
                onChange={(event) =>
                  onSenderChange(event.target.value || null)
                }
              >
                <option value="">All users</option>
                {senders
                  .filter(
                    (sender): sender is ChatInsightSender & {
                      sender_id: string;
                    } => sender.sender_id !== null,
                  )
                  .map((sender) => (
                    <option key={sender.sender_id} value={sender.sender_id}>
                      {sender.display_name}
                    </option>
                  ))}
              </select>
            </label>
          )}
      </div>

      <p className="-mt-[9px] mb-4 text-small leading-[1.5] text-ink-muted">
        Ordinary messages are grouped by UTC month. Gaps, quieter periods, and
        renewed activity are shown as data patterns, not relationship judgments.
        Service events are excluded.
      </p>

      {timeline.loading && timeline.data === null && <LoadingMessage />}
      {timeline.error && (
        <SectionError message={timeline.error} onRetry={onRetry} />
      )}
      {data && (
        <>
          {months.length === 0 ? (
            <div className={`${emptyStateClassName} p-[23px]`}>
              <h3 className={emptyStateTitleClassName}>
                No dated ordinary messages
              </h3>
              <p className={emptyStateTextClassName}>
                {data.summary.ordinary_message_count === 0
                  ? "There are no ordinary messages in this scope yet."
                  : `${formatNumber(data.summary.undated_ordinary_message_count)} ordinary messages have no reliable timestamp, so they cannot be placed on the monthly timeline.`}
              </p>
            </div>
          ) : (
            <>
              <div className="mb-3 flex flex-wrap gap-x-5 gap-y-2 text-caption text-ink-muted">
                {showDirection && (
                  <>
                    <span className="inline-flex items-center gap-2">
                      <span
                        className="size-2.5 rounded-sm bg-brand-strong"
                        aria-hidden="true"
                      />
                      Owner
                    </span>
                    <span className="inline-flex items-center gap-2">
                      <span
                        className="size-2.5 rounded-sm bg-timeline-contact"
                        aria-hidden="true"
                      />
                      Contact
                    </span>
                  </>
                )}
                {showUnknown && (
                  <span className="inline-flex items-center gap-2">
                    <span
                      className="size-2.5 rounded-sm bg-timeline-unknown"
                      aria-hidden="true"
                    />
                    Unknown direction
                  </span>
                )}
                <span className="inline-flex items-center gap-2">
                  <span
                    className="h-0 w-3 border-t-2 border-dashed border-ink-muted"
                    aria-hidden="true"
                  />
                  No messages
                </span>
              </div>
              <TimelineChart
                months={months}
                showDirection={showDirection}
              />
              <ul
                className={screenReaderOnlyClassName}
                aria-label="Monthly communication activity details"
              >
                {months.map((month) => (
                  <li key={month.month}>{monthDescription(month)}</li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}
