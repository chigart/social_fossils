import type {
  ForgottenContact,
  ForgottenContactsStatistics,
} from "../api";
import { formatDate, formatNumber } from "../utils/format";
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
} from "../constants";
import type { Resource, SortDirection } from "../types";
import {
  LoadingMessage,
  PaginationControls,
  SectionError,
  SortButton,
} from "./Feedback";
import {
  ForgottenEvidenceBadge,
  ForgottenMonthlyActivity,
  ForgottenStatusBadge,
  ForgottenSummaryCards,
  ForgottenTrend,
} from "./ForgottenContactsParts";
import { SearchPicker, type SearchPickerOption } from "./SearchPicker";

export function ForgottenContactsView({
  forgotten,
  noImportedData,
  visibleContacts,
  search,
  searchOptions,
  onSearchChange,
  sortKey,
  sortDirection,
  onSortByRank,
  onSortByLastSeen,
  onSortByName,
  onRetry,
  onPageChange,
}: {
  forgotten: Resource<ForgottenContactsStatistics>;
  noImportedData: boolean;
  visibleContacts: ForgottenContact[];
  search: string;
  searchOptions: SearchPickerOption[];
  onSearchChange: (value: string) => void;
  sortKey: "ranking_score" | "display_name" | "days_since_last_communication";
  sortDirection: SortDirection;
  onSortByRank: () => void;
  onSortByLastSeen: () => void;
  onSortByName: () => void;
  onRetry: () => void;
  onPageChange: (page: number) => void;
}) {
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
                onClick={onSortByRank}
              />
              <SortButton
                label="Last seen"
                active={sortKey === "days_since_last_communication"}
                direction={sortDirection}
                onClick={onSortByLastSeen}
              />
              <SortButton
                label="Name"
                active={sortKey === "display_name"}
                direction={sortDirection}
                onClick={onSortByName}
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
          <ForgottenSummaryCards data={forgotten.data} />
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
                        <ForgottenMonthlyActivity
                          label="Historical"
                          months={contact.historical_activity_by_month}
                        />
                        <ForgottenMonthlyActivity
                          label="Recent"
                          months={contact.recent_activity_by_month}
                        />
                      </td>
                      <td className={tableCellClassName}>
                        <ForgottenStatusBadge status={contact.classification} />
                      </td>
                      <td className={tableCellClassName}>
                        <div className="flex flex-wrap items-center gap-2">
                          <ForgottenEvidenceBadge status={contact.evidence_status} />
                          {contact.activity_decline_percentage !== null && (
                            <span className="text-caption text-ink-muted">
                              <ForgottenTrend contact={contact} />
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
