import type {
  ChatInsightSender,
  CommunicationTimelineStatistics,
} from "../api";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../constants";
import type { Resource } from "../types";
import { formatNumber } from "../utils/format";
import { LoadingMessage, SectionError } from "./Feedback";
import { MonthlyTimelineContent } from "./MonthlyTimelineContent";
import { YearlyTimelineContent } from "./YearlyTimelineContent";

export function CommunicationTimelineView({
  timeline,
  onRetry,
  senders,
  selectedSenderId,
  onSenderChange,
  showSenderSelector,
  period = "month",
}: {
  timeline: Resource<CommunicationTimelineStatistics>;
  onRetry: () => void;
  senders: ChatInsightSender[];
  selectedSenderId: string | null;
  onSenderChange: (senderId: string | null) => void;
  showSenderSelector: boolean;
  period?: "month" | "year";
}) {
  const data = timeline.data;
  const months = data?.months ?? [];
  const yearly = period === "year";

  return (
    <section
      id="communication-timeline"
      className={sectionClassName}
      aria-labelledby="communication-timeline-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>
            {yearly ? "YEARLY ACTIVITY" : "MONTHLY ACTIVITY"}
          </p>
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
                onChange={(event) => onSenderChange(event.target.value || null)}
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
        {yearly
          ? "Total ordinary messages and the owner-sent subset are grouped by UTC calendar year across all owner accounts. Owner average message size includes only dated ordinary messages sent by the owner; service events are excluded."
          : "Ordinary messages are grouped by UTC month. Gaps, quieter periods, and renewed activity are shown as data patterns, not relationship judgments. Service events are excluded."}
      </p>

      {timeline.loading && timeline.data === null && <LoadingMessage />}
      {timeline.error && (
        <SectionError message={timeline.error} onRetry={onRetry} />
      )}
      {data &&
        (months.length === 0 ? (
          <div className={`${emptyStateClassName} p-[23px]`}>
            <h3 className={emptyStateTitleClassName}>
              No dated ordinary messages
            </h3>
            <p className={emptyStateTextClassName}>
              {data.summary.ordinary_message_count === 0
                ? "There are no ordinary messages in this scope yet."
                : `${formatNumber(data.summary.undated_ordinary_message_count)} ordinary messages have no reliable timestamp, so they cannot be placed on the ${yearly ? "yearly" : "monthly"} timeline.`}
            </p>
          </div>
        ) : yearly ? (
          <YearlyTimelineContent months={months} />
        ) : (
          <MonthlyTimelineContent months={months} />
        ))}
    </section>
  );
}
