import type { OverviewStatistics } from "../api";
import { formatDate, formatNumber } from "../format";
import {
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../styles";
import type { Resource } from "../types";
import { LoadingMessage, MetricCard, SectionError } from "./Feedback";

export function OverviewView({
  overview,
  noImportedData,
  onRetry,
}: {
  overview: Resource<OverviewStatistics>;
  noImportedData: boolean | undefined;
  onRetry: () => void;
}) {
  return (
    <section
      id="overview"
      className={sectionClassName}
      aria-labelledby="overview-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>AT A GLANCE</p>
          <h2 id="overview-title" className={sectionTitleClassName}>
            Overview
          </h2>
        </div>
        <span className="pb-0.5 text-small text-ink-muted max-sm:text-caption">
          Across all imported accounts
        </span>
      </div>

      {overview.loading && overview.data === null && <LoadingMessage />}
      {overview.error && (
        <SectionError message={overview.error} onRetry={onRetry} />
      )}
      {overview.data && (
        <>
          {noImportedData && (
            <div className="mb-[14px] flex flex-wrap gap-x-3 gap-y-[7px] rounded-lg border border-border-brand bg-surface-green px-[14px] py-3 text-small text-ink-green">
              <strong>No imported data yet.</strong>
              <span className="text-ink-green-muted">
                Import a Telegram export to see your communication statistics.
              </span>
            </div>
          )}
          <div className="grid grid-cols-4 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
            <MetricCard
              label="Accounts"
              value={formatNumber(overview.data.total_imported_accounts)}
            />
            <MetricCard
              label="Chats"
              value={formatNumber(overview.data.total_chats)}
            />
            <MetricCard
              label="All messages"
              value={formatNumber(overview.data.total_messages)}
            />
            <MetricCard
              label="Ordinary messages"
              value={formatNumber(overview.data.total_ordinary_messages)}
            />
            <MetricCard
              label="Service events"
              value={formatNumber(overview.data.total_service_messages)}
            />
            <MetricCard
              label="Earliest message"
              value={formatDate(overview.data.earliest_message_timestamp)}
            />
            <MetricCard
              label="Latest message"
              value={formatDate(overview.data.latest_message_timestamp)}
            />
          </div>
        </>
      )}
    </section>
  );
}
