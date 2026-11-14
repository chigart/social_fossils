import type { CommunicationTimelineMonth } from "../api";
import { screenReaderOnlyClassName } from "../constants";
import { formatNumber } from "../utils/format";
import { TimelineChart } from "./TimelineChart";

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

export function MonthlyTimelineContent({
  months,
}: {
  months: CommunicationTimelineMonth[];
}) {
  const showDirection = months.some(
    (month) => month.owner_message_count + month.contact_message_count > 0,
  );
  const showUnknown = months.some(
    (month) => month.unknown_direction_message_count > 0,
  );

  return (
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
        points={months.map((month) => ({
          label: month.month,
          count: month.ordinary_message_count,
          ownerCount: month.owner_message_count,
          contactCount: month.contact_message_count,
          unknownCount: month.unknown_direction_message_count,
        }))}
        showDirection={showDirection}
        title="Monthly ordinary message activity"
        description="Each stacked bar shows monthly ordinary messages. Direction is separated only for messages with reliable sender identity. Empty months remain visible between active months."
        chartId="monthly-message-timeline"
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
  );
}
