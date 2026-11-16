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
import { PlatformBadge } from "./PlatformAccountBadge";
import {
  PlatformFilterSelect,
  SearchPicker,
  type SearchPickerOption,
} from "./SearchPicker";

export function ForgottenContactsView({
  forgotten,
  scope,
  noImportedData,
  visibleContacts,
  selection,
  onRetrySelection,
  search,
  platformFilter,
  searchOptions,
  onSearchChange,
  onPlatformFilterChange,
  sortKey,
  sortDirection,
  onSortByRank,
  onSortByLastSeen,
  onSortByName,
  onRetry,
  onPageChange,
}: {
  forgotten: Resource<ForgottenContactsStatistics>;
  scope: "private" | "group";
  noImportedData: boolean;
  visibleContacts: ForgottenContact[];
  selection: Resource<ForgottenContact> | null;
  onRetrySelection: () => void;
  search: string;
  platformFilter: string;
  searchOptions: SearchPickerOption[];
  onSearchChange: (value: string) => void;
  onPlatformFilterChange: (value: string) => void;
  sortKey: "ranking_score" | "display_name" | "days_since_last_communication";
  sortDirection: SortDirection;
  onSortByRank: () => void;
  onSortByLastSeen: () => void;
  onSortByName: () => void;
  onRetry: () => void;
  onPageChange: (page: number) => void;
}) {
  const isGroupScope = scope === "group";
  const title = isGroupScope ? "Group interactions" : "Forgotten contacts";
  const entityName = isGroupScope ? "participants" : "contacts";
  return (
    <section
      id={isGroupScope ? "group-interactions" : "forgotten-contacts"}
      className={sectionClassName}
      aria-labelledby={isGroupScope ? "group-interactions-title" : "forgotten-contacts-title"}
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>
            {isGroupScope ? "GROUP ACTIVITY" : "CONTACT HEALTH"}
          </p>
          <h2
            id={isGroupScope ? "group-interactions-title" : "forgotten-contacts-title"}
            className={sectionTitleClassName}
          >
            {title}
          </h2>
        </div>
        {forgotten.data &&
          (forgotten.data.contacts.length > 0 ||
            searchOptions.length > 0 ||
            platformFilter !== "") && (
          <div className="flex flex-wrap items-center gap-3 max-sm:w-full">
            <PlatformFilterSelect
              label={`Filter ${entityName} by platform`}
              value={platformFilter}
              options={searchOptions}
              onChange={onPlatformFilterChange}
            />
            <SearchPicker
              label={`Choose a ${isGroupScope ? "participant" : "forgotten contact"}`}
              value={search}
              platformFilter={platformFilter}
              options={searchOptions}
              onChange={onSearchChange}
              placeholder={`All ${entityName}`}
              searchPlaceholder={`Search ${isGroupScope ? "participant" : "contact"} name or ID`}
              allLabel={`All ${entityName}`}
              emptyMessage={`No ${entityName} match these filters.`}
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
        {isGroupScope
          ? "This view aggregates each participant’s activity across all group chats and summarizes dormant or declining interactions using historical patterns and recent activity. "
          : "This view summarizes dormant or declining one-to-one conversations using historical patterns and recent activity. "}
        The labels are descriptive heuristics and not judgments about
        relationships. Decline percentages compare recent activity with each{" "}
        {isGroupScope ? "participant’s" : "contact’s"} historical baseline.
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
          <ForgottenSummaryCards data={forgotten.data} scope={scope} />
          {noImportedData ? (
            <div className={`${emptyStateClassName} p-[23px]`}>
              <h3 className={emptyStateTitleClassName}>No imported data yet</h3>
              <p className={emptyStateTextClassName}>
                Import messaging data to compare activity over time.
              </p>
            </div>
          ) : forgotten.data.summary.eligible_contacts === 0 ? (
            <div className={`${emptyStateClassName} p-[23px]`}>
              <h3 className={emptyStateTitleClassName}>
                No eligible {isGroupScope ? "participants" : "contacts"} available
              </h3>
              <p className={emptyStateTextClassName}>
                {isGroupScope
                  ? "No identifiable participants in group chats are available for comparison."
                  : "No identifiable one-to-one contacts are available for comparison."}
              </p>
            </div>
          ) : selection?.loading ? (
            <LoadingMessage />
          ) : selection?.error ? (
            <SectionError message={selection.error} onRetry={onRetrySelection} />
          ) : visibleContacts.length === 0 ? (
            <div className={`${emptyStateClassName} p-4`}>
              <p className={emptyStateTextClassName}>
                No {entityName} match the selected search.
              </p>
            </div>
          ) : (
            <>
              {forgotten.data.summary.insufficient_data_contacts > 0 && (
                <p className="mb-3 rounded-md border border-border-input bg-surface-neutral px-3 py-2 text-small text-ink-neutral">
                  {formatNumber(forgotten.data.summary.insufficient_data_contacts)}{" "}
                  {forgotten.data.summary.insufficient_data_contacts === 1
                    ? `${isGroupScope ? "participant" : "contact"} has`
                    : `${entityName} have`}{" "}
                  insufficient history or ambiguous message direction for a reliable
                  classification. Check each {isGroupScope ? "participant’s" : "contact’s"} evidence status.
                </p>
              )}
              <PaginationControls
                pagination={search
                  ? { ...forgotten.data.pagination, page: 1, total: 1 }
                  : forgotten.data.pagination}
                onPageChange={onPageChange}
                label={`${isGroupScope ? "Interactions" : "Forgotten contacts"} pagination above table`}
              />
              <div className="w-full overflow-x-auto rounded-lg border border-border-subtle">
              <table className={`${tableClassName} min-w-[1060px]`}>
                <thead className={tableHeadClassName}>
                  <tr>
                    <th className={tableHeaderClassName} scope="col">
                      {isGroupScope ? "Participant" : "Contact"}
                    </th>
                    {isGroupScope && (
                      <th className={tableHeaderClassName} scope="col">
                        Group chats
                      </th>
                    )}
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
                        <span className="inline-flex flex-wrap items-center gap-1.5">
                          <span>{contact.display_name || "Unnamed contact"}</span>
                          {contact.platforms.map((platform) => (
                            <PlatformBadge key={platform} platform={platform} />
                          ))}
                        </span>
                      </th>
                      {isGroupScope && (
                        <td className={numericTableCellClassName}>
                          {formatNumber(contact.interaction_chat_count)}
                        </td>
                      )}
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
            pagination={search
              ? { ...forgotten.data.pagination, page: 1, total: 1 }
              : forgotten.data.pagination}
            onPageChange={onPageChange}
            label={`${isGroupScope ? "Interactions" : "Forgotten contacts"} pagination below table`}
          />
        </>
      )}
    </section>
  );
}
