import type {
  CommunicationTimelineMonth,
  CommunicationTimelineStatistics,
} from "../api";
import { formatNumber } from "../format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  screenReaderOnlyClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../styles";
import type { Resource } from "../types";
import { LoadingMessage, MetricCard, SectionError } from "./Feedback";
import { PlatformAccountBadge } from "./PlatformAccountBadge";

export type TimelineContactOption = {
  canonicalIdentityId: number;
  displayName: string;
  platformUserId: string | null;
};

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
  const slotWidth = width / months.length;
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
                x2={width - 8}
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
  contactOptions,
  selectedContactId,
  onContactChange,
  onRetry,
}: {
  timeline: Resource<CommunicationTimelineStatistics>;
  contactOptions: TimelineContactOption[];
  selectedContactId: number | null;
  onContactChange: (contactId: number | null) => void;
  onRetry: () => void;
}) {
  const data = timeline.data;
  const months = data?.months ?? [];
  const showDirection = months.some(
    (month) => month.owner_message_count + month.contact_message_count > 0,
  );
  const showUnknown = months.some(
    (month) => month.unknown_direction_message_count > 0,
  );
  const activeDays = months.reduce((total, month) => total + month.active_days, 0);
  const selectedContact = contactOptions.find(
    (contact) => contact.canonicalIdentityId === selectedContactId,
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
        <label className="flex min-w-[220px] flex-col gap-1 text-caption font-semibold text-ink-muted max-sm:w-full">
          Timeline scope
          <select
            className="min-h-[38px] rounded-[7px] border border-border-input bg-surface px-3 py-2 text-small text-ink outline-none focus:border-brand focus:ring-[3px] focus:ring-focus-ring"
            value={selectedContactId ?? ""}
            onChange={(event) =>
              onContactChange(
                event.currentTarget.value === ""
                  ? null
                  : Number(event.currentTarget.value),
              )
            }
            aria-label="Timeline scope"
          >
            <option value="">Combined owner history</option>
            {contactOptions.map((contact) => (
              <option
                key={contact.canonicalIdentityId}
                value={contact.canonicalIdentityId}
              >
                {contact.displayName}
                {contact.platformUserId
                  ? ` · ${contact.platformUserId}`
                  : ""}
              </option>
            ))}
          </select>
        </label>
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
          <div className="mb-5 grid grid-cols-4 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
            <MetricCard
              label="Ordinary messages"
              value={formatNumber(data.summary.ordinary_message_count)}
            />
            <MetricCard
              label="Dated messages"
              value={formatNumber(data.summary.dated_ordinary_message_count)}
            />
            <MetricCard
              label="Undated messages"
              value={formatNumber(data.summary.undated_ordinary_message_count)}
            />
            <MetricCard
              label="Active days"
              value={formatNumber(activeDays)}
              detail="sum of monthly active days"
            />
            <MetricCard
              label="Owner messages"
              value={formatNumber(data.summary.owner_message_count)}
            />
            <MetricCard
              label="Contact messages"
              value={formatNumber(data.summary.contact_message_count)}
            />
            <MetricCard
              label="Unknown direction"
              value={formatNumber(data.summary.unknown_direction_message_count)}
            />
          </div>

          <p className="mb-3 text-small text-ink-muted">
            Scope:{" "}
            <strong className="font-semibold text-ink">
              {data.summary.scope === "owner"
                ? "Combined owner history"
                : selectedContact?.displayName ?? "Selected canonical contact"}
            </strong>
            {" · "}
            {formatNumber(data.summary.source_account_count)} source{" "}
            {data.summary.source_account_count === 1 ? "account" : "accounts"}
            {data.summary.source_account_labels.length > 0 && (
              <>
                {" · "}
                {data.summary.source_account_labels.map((label) => (
                  <PlatformAccountBadge
                    key={label}
                    platform="telegram"
                    accountLabel={label}
                  />
                ))}
              </>
            )}
          </p>

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
              <TimelineChart months={months} showDirection={showDirection} />
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
