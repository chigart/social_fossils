import type { OverviewStatistics } from "../api";
import type { CommunicationTimelineStatistics } from "../api";
import type { CloseFriendsTimelineStatistics } from "../api";
import type { OwnerReplyTimelineStatistics } from "../api";
import { formatDate, formatNumber } from "../utils/format";
import {
  numericTableCellClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
  tableCellClassName,
  tableClassName,
  tableContainerClassName,
  tableHeadClassName,
  tableHeaderClassName,
  tableRowClassName,
  tableRowTitleClassName,
} from "../constants";
import type { Resource } from "../types";
import { LoadingMessage, MetricCard, SectionError } from "./Feedback";
import { CommunicationTimelineView } from "./CommunicationTimelineView";
import { CloseFriendsTimelineView } from "./CloseFriendsTimelineView";
import { OwnerReplyTimelineView } from "./OwnerReplyTimelineView";

export function OverviewView({
  overview,
  timeline,
  closeFriendsTimeline,
  ownerReplyTimeline,
  noImportedData,
  selectedTimelineAccountId,
  onRetry,
  onRetryTimeline,
  onRetryCloseFriendsTimeline,
  onRetryOwnerReplyTimeline,
  onTimelineAccountChange,
}: {
  overview: Resource<OverviewStatistics>;
  timeline: Resource<CommunicationTimelineStatistics>;
  closeFriendsTimeline: Resource<CloseFriendsTimelineStatistics>;
  ownerReplyTimeline: Resource<OwnerReplyTimelineStatistics>;
  noImportedData: boolean | undefined;
  selectedTimelineAccountId: number | null;
  onRetry: () => void;
  onRetryTimeline: (accountId: number | null) => void;
  onRetryCloseFriendsTimeline: () => void;
  onRetryOwnerReplyTimeline: () => void;
  onTimelineAccountChange: (accountId: number | null) => void;
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
          {selectedTimelineAccountId === null
            ? "Combined owner scope"
            : "Single imported account scope"}
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
                Import messaging exports to see your communication statistics.
              </span>
            </div>
          )}
          <div className="grid grid-cols-5 gap-3 max-[1000px]:grid-cols-3 max-sm:grid-cols-2 max-sm:gap-2">
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
              label="Earliest message"
              value={formatDate(overview.data.earliest_message_timestamp)}
            />
            <MetricCard
              label="Latest message"
              value={formatDate(overview.data.latest_message_timestamp)}
            />
          </div>
          <div className="mt-6">
            <CommunicationTimelineView
              timeline={timeline}
              onRetry={() => onRetryTimeline(selectedTimelineAccountId)}
              senders={[]}
              selectedSenderId={null}
              onSenderChange={() => {}}
              showSenderSelector={false}
              accounts={overview.data.imported_accounts}
              selectedAccountId={selectedTimelineAccountId}
              onAccountChange={onTimelineAccountChange}
              period="year"
            />
          </div>
          <div className="mt-6">
            <CloseFriendsTimelineView
              timeline={closeFriendsTimeline}
              onRetry={onRetryCloseFriendsTimeline}
            />
          </div>
          <div className="mt-6">
            <OwnerReplyTimelineView
              timeline={ownerReplyTimeline}
              onRetry={onRetryOwnerReplyTimeline}
            />
          </div>
          <div className="mt-6">
            <h3 className="mb-3 text-subheading font-bold text-ink">
              Imported accounts
            </h3>
            {overview.data.imported_accounts.length > 0 ? (
              <div className={tableContainerClassName}>
                <table className={tableClassName}>
                  <thead className={tableHeadClassName}>
                    <tr>
                      <th className={tableHeaderClassName} scope="col">
                        Platform
                      </th>
                      <th className={tableHeaderClassName} scope="col">
                        Name
                      </th>
                      <th className={tableHeaderClassName} scope="col">
                        Username
                      </th>
                      <th className={tableHeaderClassName} scope="col">
                        Total messages
                      </th>
                      <th className={tableHeaderClassName} scope="col">
                        Text volume
                      </th>
                      <th className={tableHeaderClassName} scope="col">
                        Activity interval
                      </th>
                      <th className={tableHeaderClassName} scope="col">
                        Total contacts
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.data.imported_accounts.map((account) => (
                      <tr className={tableRowClassName} key={account.id}>
                        <th className={tableRowTitleClassName} scope="row">
                          {account.platform}
                        </th>
                        <td className={tableCellClassName}>{account.name}</td>
                        <td className={tableCellClassName}>
                          {account.username || "—"}
                        </td>
                        <td className={numericTableCellClassName}>
                          {formatNumber(account.total_messages)}
                        </td>
                        <td className={numericTableCellClassName}>
                          {formatNumber(account.total_text_length)}
                        </td>
                        <td className={tableCellClassName}>
                          {formatDate(account.earliest_message_timestamp)} -{" "}
                          {formatDate(account.latest_message_timestamp)}
                        </td>
                        <td className={numericTableCellClassName}>
                          {formatNumber(account.total_contacts)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="m-0 text-small text-ink-muted">
                No imported accounts.
              </p>
            )}
          </div>
        </>
      )}
    </section>
  );
}
