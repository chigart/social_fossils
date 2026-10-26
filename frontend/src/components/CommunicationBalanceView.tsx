import type {
  CommunicationBalanceClassification,
  CommunicationBalanceContact,
  CommunicationBalanceStatistics,
} from "../api";
import { formatNumber } from "../format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../styles";
import type { Resource, SortDirection } from "../types";
import { LoadingMessage, MetricCard, SectionError } from "./Feedback";
import { CommunicationBalanceControls } from "./CommunicationBalanceControls";
import { CommunicationBalanceTable } from "./CommunicationBalanceTable";
import {
  type BalanceSortKey,
  sortCommunicationBalanceContacts,
} from "./communicationBalanceUtils";
import type { SearchPickerOption } from "./SearchPicker";

export { sortCommunicationBalanceContacts };
export type { BalanceSortKey };

function SummaryCards({ data }: { data: CommunicationBalanceStatistics }) {
  const { summary } = data;
  return (
    <div className="mb-5 grid grid-cols-4 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
      <MetricCard label="Eligible contacts" value={formatNumber(summary.eligible_contacts)} />
      <MetricCard label="Balanced" value={formatNumber(summary.balanced_contacts)} />
      <MetricCard label="Mostly owner" value={formatNumber(summary.mostly_owner_contacts)} />
      <MetricCard label="Mostly contact" value={formatNumber(summary.mostly_contact_contacts)} />
      <MetricCard label="Strongly owner" value={formatNumber(summary.strongly_owner_contacts)} />
      <MetricCard label="Strongly contact" value={formatNumber(summary.strongly_contact_contacts)} />
      <MetricCard
        label="Insufficient data"
        value={formatNumber(summary.insufficient_data_contacts)}
      />
      <MetricCard
        label="Total text exchanged"
        value={formatNumber(summary.total_text_length)}
        detail="characters"
      />
    </div>
  );
}

export function CommunicationBalanceView({
  balance,
  visibleContacts,
  search,
  onSearchChange,
  classification,
  onClassificationChange,
  sortKey,
  sortDirection,
  onSortKeyChange,
  onSortDirectionChange,
  onRetry,
}: {
  balance: Resource<CommunicationBalanceStatistics>;
  visibleContacts: CommunicationBalanceContact[];
  search: string;
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
            searchOptions={balance.data.contacts.map((contact, index) => ({
              value: String(index),
              label: contact.display_name || "Unnamed contact",
              platforms: contact.platforms,
              searchTerms: [
                ...contact.platform_user_ids,
                ...contact.source_account_labels,
              ],
            } satisfies SearchPickerOption))}
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
          <SummaryCards data={balance.data} />
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
            <CommunicationBalanceTable contacts={visibleContacts} />
          )}
        </>
      )}
    </section>
  );
}
