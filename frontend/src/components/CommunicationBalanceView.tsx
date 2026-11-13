import type {
  CommunicationBalanceClassification,
  CommunicationBalanceContact,
  CommunicationBalanceStatistics,
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
import type { Resource, SortDirection } from "../types";
import {
  LoadingMessage,
  PaginationControls,
  SectionError,
} from "./Feedback";
import { CommunicationBalanceControls } from "./CommunicationBalanceControls";
import { CommunicationBalanceSummary } from "./CommunicationBalanceSummary";
import { CommunicationBalanceTable } from "./CommunicationBalanceTable";
import type { BalanceSortKey } from "../utils/communicationBalance";
import type { SearchPickerOption } from "./SearchPicker";

export function CommunicationBalanceView({
  balance,
  visibleContacts,
  search,
  searchOptions,
  onSearchChange,
  classification,
  onClassificationChange,
  sortKey,
  sortDirection,
  onSortKeyChange,
  onSortDirectionChange,
  onRetry,
  onPageChange,
}: {
  balance: Resource<CommunicationBalanceStatistics>;
  visibleContacts: CommunicationBalanceContact[];
  search: string;
  searchOptions: SearchPickerOption[];
  onSearchChange: (value: string) => void;
  classification: CommunicationBalanceClassification | "all";
  onClassificationChange: (
    value: CommunicationBalanceClassification | "all",
  ) => void;
  sortKey: BalanceSortKey;
  sortDirection: SortDirection;
  onSortKeyChange: (value: BalanceSortKey) => void;
  onSortDirectionChange: (value: SortDirection) => void;
  onRetry: () => void;
  onPageChange: (page: number) => void;
}) {
  return (
    <section
      id="communication-balance"
      className={sectionClassName}
      aria-labelledby="communication-balance-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>TEXT RECIPROCITY</p>
          <h2 id="communication-balance-title" className={sectionTitleClassName}>
            Communication balance
          </h2>
        </div>
        {balance.data && balance.data.contacts.length > 0 && (
          <CommunicationBalanceControls
            search={search}
            onSearchChange={onSearchChange}
            searchOptions={searchOptions}
            classification={classification}
            onClassificationChange={onClassificationChange}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onSortKeyChange={onSortKeyChange}
            onSortDirectionChange={onSortDirectionChange}
          />
        )}
      </div>

      <p className="-mt-[9px] mb-4 text-small leading-[1.5] text-ink-muted">
        Text volume counts Unicode code points in normalized ordinary-message text.
        Spaces and punctuation count; media-only messages and service events do not.
        Only eligible one-to-one personal chats with an identified owner and contact
        are included. These descriptive labels are not judgments about relationships.
      </p>

      {balance.loading && balance.data === null && <LoadingMessage />}
      {balance.error && (
        <SectionError message={balance.error} onRetry={onRetry} />
      )}
      {balance.data && (
        <>
          <CommunicationBalanceSummary data={balance.data} />
          {balance.data.contacts.length === 0 ? (
            <div className={`${emptyStateClassName} p-[23px]`}>
              <h3 className={emptyStateTitleClassName}>
                No eligible contacts available
              </h3>
              <p className={emptyStateTextClassName}>
                Communication balance needs an identified owner and contact in an
                eligible one-to-one personal chat.
              </p>
            </div>
          ) : visibleContacts.length === 0 ? (
            <div className={`${emptyStateClassName} p-4`}>
              <p className={emptyStateTextClassName}>
                No contacts match the selected search and classification.
              </p>
            </div>
          ) : (
            <>
              <PaginationControls
                pagination={balance.data.pagination}
                onPageChange={onPageChange}
                label="Communication balance pagination above table"
              />
              <CommunicationBalanceTable contacts={visibleContacts} />
            </>
          )}
          <PaginationControls
            pagination={balance.data.pagination}
            onPageChange={onPageChange}
            label="Communication balance pagination below table"
          />
        </>
      )}
    </section>
  );
}
