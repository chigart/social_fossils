import { useMemo } from "react";
import type {
  ForgottenContact,
  ForgottenContactsStatistics,
} from "../api";
import { formatDate, formatNumber } from "../format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  numericTableCellClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
  tableCellClassName,
  tableClassName,
  tableHeadClassName,
  tableHeaderClassName,
  tableRowClassName,
  tableRowTitleClassName,
} from "../styles";
import type { Resource, SortDirection } from "../types";
import {
  LoadingMessage,
  MetricCard,
  PaginationControls,
  SectionError,
  SortButton,
} from "./Feedback";
import { SearchPicker } from "./SearchPicker";

export const forgottenClassificationLabels = {
  inactive: "Inactive",
  activity_declined: "Declining",
  active: "Active",
  insufficient_data: "Insufficient data",
} as const;

export const forgottenEvidenceLabels = {
  reliable_baseline: "Reliable baseline",
  insufficient_history: "Insufficient history",
  insufficient_baseline: "Insufficient baseline",
  ambiguous_direction: "Ambiguous direction",
} as const;

function StatusBadge({ status }: { status: ForgottenContact["classification"] }) {
  const className =
    status === "active"
      ? "border border-border-brand bg-surface-green text-ink-green"
      : status === "activity_declined"
        ? "border border-border-warning bg-surface-warning text-ink-warning"
        : status === "inactive"
          ? "border border-border-subtle bg-surface-muted text-ink"
          : "border border-border-input bg-surface-neutral text-ink-neutral";

  return (
    <span className={`inline-block whitespace-nowrap rounded px-[7px] py-1 text-label font-semibold ${className}`}>
      {forgottenClassificationLabels[status]}
    </span>
  );
}

function EvidenceBadge({
  status,
}: {
  status: ForgottenContact["evidence_status"];
}) {
  return (
    <span className="inline-block whitespace-nowrap rounded border border-border-input bg-surface-neutral px-[7px] py-1 text-label font-semibold text-ink-neutral">
      {forgottenEvidenceLabels[status]}
    </span>
  );
}

function TrendCell({ contact }: { contact: ForgottenContact }) {
  if (contact.activity_decline_percentage === null) {
    return <span className="text-ink-muted">—</span>;
  }

  const label = `${formatNumber(Math.round(contact.activity_decline_percentage))}%`;
  return <span className="tabular-nums">{label}</span>;
}

function MonthlyActivity({
  label,
  months,
}: {
  label: string;
  months: ForgottenContact["historical_activity_by_month"];
}) {
  const visibleMonths = months.slice(-6);
  const maxCount = Math.max(...visibleMonths.map((month) => month.total_message_count), 1);

  if (visibleMonths.length === 0) {
    return (
      <p className="m-0 text-caption text-ink-muted">
        {label}: no dated activity
      </p>
    );
  }

  const description = visibleMonths
    .map((month) => `${month.month}: ${month.total_message_count} messages`)
    .join(", ");

  return (
    <div
      className="mb-2 last:mb-0"
      role="img"
      aria-label={`${label} monthly activity: ${description}`}
    >
      <p className="mb-1 m-0 text-caption font-semibold text-ink-muted">{label}</p>
      <div className="flex min-w-[250px] items-end gap-1">
        {visibleMonths.map((month) => (
          <div
            className="flex min-w-0 flex-1 flex-col items-center gap-1"
            key={month.month}
          >
            <span className="text-caption tabular-nums text-ink-muted">
              {formatNumber(month.total_message_count)}
            </span>
            <span
              className="w-full rounded-t bg-brand"
              style={{
                height: `${Math.max(4, (month.total_message_count / maxCount) * 28)}px`,
              }}
            />
            <span className="text-[10px] text-ink-muted">{month.month}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SummaryCards({ data }: { data: ForgottenContactsStatistics }) {
  const { summary } = data;
  return (
    <div className="mb-5 grid grid-cols-5 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
      <MetricCard label="Eligible contacts" value={formatNumber(summary.eligible_contacts)} />
      <MetricCard
        label="Meaningful history"
        value={formatNumber(summary.meaningful_historical_contacts)}
      />
      <MetricCard
        label="Inactive"
        value={formatNumber(summary.currently_inactive_contacts)}
      />
      <MetricCard
        label="Declining"
        value={formatNumber(summary.declining_activity_contacts)}
      />
      <MetricCard
        label="Insufficient data"
        value={formatNumber(summary.insufficient_data_contacts)}
      />
    </div>
  );
}

export function ForgottenContactsView({
  forgotten,
  noImportedData,
  visibleContacts,
  search,
  onSearchChange,
  sortKey,
  sortDirection,
  onSortKeyChange,
  onSortDirectionChange,
  onRetry,
  onPageChange,
}: {
  forgotten: Resource<ForgottenContactsStatistics>;
  noImportedData: boolean;
  visibleContacts: ForgottenContact[];
  search: string;
  onSearchChange: (value: string) => void;
  sortKey: "ranking_score" | "display_name" | "days_since_last_communication";
  sortDirection: SortDirection;
  onSortKeyChange: (
    value: "ranking_score" | "display_name" | "days_since_last_communication",
  ) => void;
  onSortDirectionChange: (value: SortDirection) => void;
  onRetry: () => void;
  onPageChange: (page: number) => void;
}) {
  const searchOptions = useMemo(
    () =>
      forgotten.data?.options?.length
        ? forgotten.data.options.map((option) => ({
            value: option.value,
            label: option.label,
            platforms: option.platforms,
            searchTerms: option.search_terms,
          }))
        : (forgotten.data?.contacts ?? []).map((contact, index) => ({
            value: String(index),
            label: contact.display_name || "Unnamed contact",
            platforms: contact.platforms,
            searchTerms: [
              ...contact.platform_user_ids,
              ...contact.source_account_labels,
            ],
          })),
    [forgotten.data?.options, forgotten.data?.contacts],
  );

  const toggleSort = (
    key: "ranking_score" | "display_name" | "days_since_last_communication",
    defaultDirection: SortDirection,
  ) => {
    if (sortKey === key) {
      onSortDirectionChange(sortDirection === "asc" ? "desc" : "asc");
      return;
    }

    onSortKeyChange(key);
    onSortDirectionChange(defaultDirection);
  };

  return (
    <section
      id="forgotten-contacts"
      className={sectionClassName}
      aria-labelledby="forgotten-contacts-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>CONTACT HEALTH</p>
          <h2 id="forgotten-contacts-title" className={sectionTitleClassName}>
            Forgotten contacts
          </h2>
        </div>
        {forgotten.data && forgotten.data.contacts.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 max-sm:w-full">
            <SearchPicker
              label="Choose a forgotten contact"
              value={search}
              options={searchOptions}
              onChange={onSearchChange}
              placeholder="All contacts"
              searchPlaceholder="Search contact name or ID"
              allLabel="All contacts"
              emptyMessage="No contacts match these filters."
            />
            <div className="flex items-center gap-3 text-small text-ink-muted">
              <SortButton
                label="Rank"
                active={sortKey === "ranking_score"}
                direction={sortDirection}
                onClick={() => toggleSort("ranking_score", "desc")}
              />
              <SortButton
                label="Last seen"
                active={sortKey === "days_since_last_communication"}
                direction={sortDirection}
                onClick={() => toggleSort("days_since_last_communication", "desc")}
              />
              <SortButton
                label="Name"
                active={sortKey === "display_name"}
                direction={sortDirection}
                onClick={() => toggleSort("display_name", "asc")}
              />
            </div>
          </div>
        )}
      </div>

      <p className="-mt-[9px] mb-4 text-small leading-[1.5] text-ink-muted">
        This view summarises dormant or declining conversations using historical
        patterns and recent activity. The labels are descriptive heuristics and not
        judgments about relationships. Decline percentages compare recent activity
        with each contact’s historical baseline.
      </p>
      {forgotten.data && (
        <p className="mb-4 text-caption text-ink-muted">
          Scope: Combined owner data · {formatNumber(forgotten.data.summary.source_account_count)}{" "}
          source{" "}
          {forgotten.data.summary.source_account_count === 1 ? "account" : "accounts"}
        </p>
      )}

      {forgotten.loading && forgotten.data === null && <LoadingMessage />}
      {forgotten.error && <SectionError message={forgotten.error} onRetry={onRetry} />}
      {forgotten.data && (
        <>
          <SummaryCards data={forgotten.data} />
          {noImportedData ? (
            <div className={`${emptyStateClassName} p-[23px]`}>
              <h3 className={emptyStateTitleClassName}>No imported data yet</h3>
              <p className={emptyStateTextClassName}>
                Import a Telegram export to compare contact activity over time.
              </p>
            </div>
          ) : forgotten.data.summary.eligible_contacts === 0 ? (
            <div className={`${emptyStateClassName} p-[23px]`}>
              <h3 className={emptyStateTitleClassName}>No eligible contacts available</h3>
              <p className={emptyStateTextClassName}>
                No identifiable one-to-one contacts are available for comparison.
              </p>
            </div>
          ) : visibleContacts.length === 0 ? (
            <div className={`${emptyStateClassName} p-4`}>
              <p className={emptyStateTextClassName}>
                No contacts match the selected search.
              </p>
            </div>
          ) : (
            <>
              {forgotten.data.summary.insufficient_data_contacts > 0 && (
                <p className="mb-3 rounded-md border border-border-input bg-surface-neutral px-3 py-2 text-small text-ink-neutral">
                  {formatNumber(forgotten.data.summary.insufficient_data_contacts)}{" "}
                  {forgotten.data.summary.insufficient_data_contacts === 1
                    ? "contact has"
                    : "contacts have"}{" "}
                  insufficient history or ambiguous message direction for a reliable
                  classification. Check each contact’s evidence status.
                </p>
              )}
              <PaginationControls
                pagination={forgotten.data.pagination}
                onPageChange={onPageChange}
                label="Forgotten contacts pagination above table"
              />
              <div className="w-full overflow-x-auto rounded-lg border border-border-subtle">
              <table className={`${tableClassName} min-w-[1060px]`}>
                <thead className={tableHeadClassName}>
                  <tr>
                    <th className={tableHeaderClassName} scope="col">Contact</th>
                    <th className={tableHeaderClassName} scope="col">Last seen</th>
                    <th className={tableHeaderClassName} scope="col">Days</th>
                    <th className={tableHeaderClassName} scope="col">Recent</th>
                    <th className={tableHeaderClassName} scope="col">Monthly activity</th>
                    <th className={tableHeaderClassName} scope="col">Status</th>
                    <th className={tableHeaderClassName} scope="col">Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleContacts.map((contact) => (
                    <tr className={tableRowClassName} key={`${contact.account_id}-${contact.contact_id}`}>
                      <th className={tableRowTitleClassName} scope="row">
                        {contact.display_name || "Unnamed contact"}
                      </th>
                      <td className={tableCellClassName}>{formatDate(contact.last_message_at)}</td>
                      <td className={numericTableCellClassName}>
                        {contact.days_since_last_communication === null
                          ? "—"
                          : formatNumber(contact.days_since_last_communication)}
                      </td>
                      <td className={numericTableCellClassName}>
                        <span className="tabular-nums">
                          {formatNumber(contact.recent_message_count)} / {formatNumber(contact.historical_message_count)}
                        </span>
                      </td>
                      <td className={tableCellClassName}>
                        <MonthlyActivity
                          label="Historical"
                          months={contact.historical_activity_by_month}
                        />
                        <MonthlyActivity
                          label="Recent"
                          months={contact.recent_activity_by_month}
                        />
                      </td>
                      <td className={tableCellClassName}>
                        <StatusBadge status={contact.classification} />
                      </td>
                      <td className={tableCellClassName}>
                        <div className="flex flex-wrap items-center gap-2">
                          <EvidenceBadge status={contact.evidence_status} />
                          {contact.activity_decline_percentage !== null && (
                            <span className="text-caption text-ink-muted">
                              <TrendCell contact={contact} />
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </>
          )}
          <PaginationControls
            pagination={forgotten.data.pagination}
            onPageChange={onPageChange}
            label="Forgotten contacts pagination below table"
          />
        </>
      )}
    </section>
  );
}
