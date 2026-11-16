import type { CloseFriendsTimelineStatistics } from "../api";
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
import { LoadingMessage, SectionError } from "./Feedback";
import { TimelineChart } from "./TimelineChart";

export function CloseFriendsTimelineView({
  timeline,
  onRetry,
}: {
  timeline: Resource<CloseFriendsTimelineStatistics>;
  onRetry: () => void;
}) {
  const years = timeline.data?.years ?? [];

  return (
    <section
      id="close-friends-timeline"
      className={sectionClassName}
      aria-labelledby="close-friends-timeline-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>YEARLY RELATIONSHIPS</p>
          <h2
            id="close-friends-timeline-title"
            className={sectionTitleClassName}
          >
            Close friends timeline
          </h2>
        </div>
      </div>
      <p className="-mt-[9px] mb-4 text-small leading-[1.5] text-ink-muted">
        Counts direct-chat contacts with at least 200 exchanged text messages in
        a year who stayed in touch with an owner-sent text each following year.
        The first partial year is omitted; the last partial year repeats the
        previous year.
      </p>
      {timeline.loading && timeline.data === null && <LoadingMessage />}
      {timeline.error && (
        <SectionError message={timeline.error} onRetry={onRetry} />
      )}
      {timeline.data &&
        (years.length === 0 ? (
          <div className={`${emptyStateClassName} p-[23px]`}>
            <h3 className={emptyStateTitleClassName}>
              No complete yearly history
            </h3>
            <p className={emptyStateTextClassName}>
              Close-friend counts need at least one complete calendar year of
              messaging history.
            </p>
          </div>
        ) : (
          <>
            <h3 className="mb-2 text-small font-bold text-ink">
              Close friends by year
            </h3>
            <TimelineChart
              points={years.map(({ year, close_friend_count }) => ({
                label: String(year),
                count: close_friend_count,
              }))}
              showDirection={false}
              title="Close friends per year"
              description="Number of contacts qualifying as Close in each UTC calendar year."
              chartId="close-friends-yearly-timeline-chart"
              heatmap
            />
            <ul
              className={screenReaderOnlyClassName}
              aria-label="Close friends per year details"
            >
              {years.map(({ year, close_friend_count }) => (
                <li key={year}>
                  {year}: {formatNumber(close_friend_count)} close friends
                </li>
              ))}
            </ul>
          </>
        ))}
    </section>
  );
}
