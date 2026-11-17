import type { OwnerReplyTimelineStatistics } from "../api";
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
import { formatNumber } from "../utils/format";
import { formatResponseTime } from "../utils/formatResponseTime";
import { LoadingMessage, SectionError } from "./Feedback";
import { TimelineChart } from "./TimelineChart";

export function OwnerReplyTimelineView({
  timeline,
  onRetry,
}: {
  timeline: Resource<OwnerReplyTimelineStatistics>;
  onRetry: () => void;
}) {
  const years = timeline.data?.years ?? [];

  return (
    <section
      id="owner-reply-timeline"
      className={sectionClassName}
      aria-labelledby="owner-reply-timeline-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>YEARLY REPLY TEMPO</p>
          <h2
            id="owner-reply-timeline-title"
            className={sectionTitleClassName}
          >
            Owner average reply time
          </h2>
        </div>
      </div>
      <p className="-mt-[9px] mb-4 text-small leading-[1.5] text-ink-muted">
        Average time from the contact’s first message to the owner’s first
        response in a contact-opened one-on-one conversation, combined across
        all imported accounts and platforms. Each Insights 12-hour session
        contributes at most one reply time; yearly averages require at least 5
        measured sessions.
      </p>
      {timeline.loading && timeline.data === null && <LoadingMessage />}
      {timeline.error && (
        <SectionError message={timeline.error} onRetry={onRetry} />
      )}
      {timeline.data &&
        (years.length === 0 ? (
          <div className={`${emptyStateClassName} p-[23px]`}>
            <h3 className={emptyStateTitleClassName}>
              No measured owner replies
            </h3>
            <p className={emptyStateTextClassName}>
              Reply times require a one-on-one conversation with a reliable
              timestamp and owner/contact direction.
            </p>
          </div>
        ) : (
          <>
            <h3 className="mb-2 text-small font-bold text-ink">
              Average owner reply time by year
            </h3>
            <TimelineChart
              points={years.map(({ year, average_response_seconds }) => ({
                label: String(year),
                count: average_response_seconds ?? 0,
                notAvailable: average_response_seconds === null,
              }))}
              showDirection={false}
              title="Owner average reply time per year"
              description="Mean elapsed time, in seconds, from the contact's first message to the owner's first response in a contact-opened one-on-one session across imported accounts and platforms, grouped by UTC year. Each session contributes at most once; years without measured replies are marked N/A."
              chartId="owner-reply-yearly-timeline-chart"
              heatmap
              formatTick={formatResponseTime}
              formatCount={formatResponseTime}
            />
            <ul
              className={screenReaderOnlyClassName}
              aria-label="Owner average reply time by year details"
            >
              {years.map(({ year, average_response_seconds }) => (
                <li key={year}>
                  {average_response_seconds === null
                    ? `${year}: N/A average reply time`
                    : `${year}: ${formatResponseTime(average_response_seconds)} average reply time (${formatNumber(average_response_seconds)} seconds)`}
                </li>
              ))}
            </ul>
          </>
        ))}
    </section>
  );
}
