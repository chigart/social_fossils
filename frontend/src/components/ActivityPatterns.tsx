import type {
  ActivityPeriodCount,
  ChatInsightSender,
} from "../api";
import {
  chatInsightsCardClassName,
  chatInsightsEmptyTextClassName,
  chatInsightsSectionTitleClassName,
} from "../constants";
import { formatNumber } from "../utils/format";
import { TimelineChart } from "./TimelineChart";

function ActivityCountChart({
  title,
  periods,
}: {
  title: string;
  periods: ActivityPeriodCount[];
}) {
  const maximum = Math.max(0, ...periods.map(({ count }) => count));

  return (
    <section className={chatInsightsCardClassName} aria-label={title}>
      <h3 className={chatInsightsSectionTitleClassName}>{title}</h3>
      {maximum === 0 ? (
        <p className={chatInsightsEmptyTextClassName}>
          No dated ordinary-message activity.
        </p>
      ) : (
        <TimelineChart
          points={periods.map(({ period, count }) => ({
            label: period,
            displayLabel: title.includes("month") ? period.slice(0, 3) : period,
            count,
          }))}
          showDirection={false}
          title={title}
          description={`${title}. Vertical bars show dated ordinary-message counts. Color intensity follows activity count, matching the Overview heatmap.`}
          chartId={title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}
          heatmap
          fitContainer
          barWidthRatio={0.83}
          maxBarWidth={80}
          labelFontSize={13.5}
        />
      )}
      {maximum > 0 && (
        <ul className="sr-only" aria-label={`${title} details`}>
          {periods.map(({ period, count }) => (
            <li key={period}>
              {period}: {formatNumber(count)} messages
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ActivityPatterns({
  senders,
  averageActivityTime,
  weekdayActivity,
  monthActivity,
}: {
  senders: ChatInsightSender[];
  averageActivityTime: string | null;
  weekdayActivity: ActivityPeriodCount[];
  monthActivity: ActivityPeriodCount[];
}) {
  const sendersWithActivityTime = senders.filter(
    (sender) => sender.average_activity_time !== null,
  ).sort(
    (left, right) =>
      (left.average_activity_time ?? "").localeCompare(
        right.average_activity_time ?? "",
      ) || left.display_name.localeCompare(right.display_name),
  );

  return (
    <div className="mb-5">
      <div className="grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        <ActivityCountChart
          title="Activity by weekday (UTC)"
          periods={weekdayActivity}
        />
        <ActivityCountChart
          title="Activity by month (UTC)"
          periods={monthActivity}
        />
      </div>
      <section
        className={`${chatInsightsCardClassName} mt-3`}
        aria-label="Average activity time"
      >
        <h3 className={chatInsightsSectionTitleClassName}>
          Average activity time
        </h3>
        <p className="mb-3 text-small text-ink-muted">
          Circular mean of dated ordinary-message times, shown in UTC.
        </p>
        <p className="mb-3 text-small text-ink">
          Overall average:{" "}
          <time className="font-semibold tabular-nums">
            {averageActivityTime ?? "—"}
          </time>
        </p>
        {sendersWithActivityTime.length === 0 ? (
          <p className={chatInsightsEmptyTextClassName}>
            No sender activity with timestamps available.
          </p>
        ) : (
          <ul
            className="m-0 flex flex-wrap gap-x-6 gap-y-2 p-0"
            aria-label="Average activity time by person"
          >
            {sendersWithActivityTime.map((sender, index) => (
              <li
                key={`${sender.sender_id ?? sender.display_name}-${index}`}
                className="flex items-center gap-2 text-small"
              >
                <span className="text-ink-muted">{sender.display_name}</span>
                <time className="font-semibold tabular-nums text-ink">
                  {sender.average_activity_time}
                </time>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
