import type { CommunicationBalanceClassification } from "../api";
import {
  classifications,
  classificationLabels,
  type BalanceSortKey,
} from "./communicationBalanceUtils";
import {
  screenReaderOnlyClassName,
  searchInputClassName,
  searchLabelClassName,
} from "../styles";
import type { SortDirection } from "../types";

export function CommunicationBalanceControls({
  search,
  onSearchChange,
  classification,
  onClassificationChange,
  sortKey,
  sortDirection,
  onSortKeyChange,
  onSortDirectionChange,
}: {
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
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 max-sm:w-full">
      <label className={searchLabelClassName}>
        <span className={screenReaderOnlyClassName}>
          Search balance contacts by display name
        </span>
        <input
          className={searchInputClassName}
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search contacts"
        />
      </label>
      <label className="text-small text-ink-muted">
        <span className={screenReaderOnlyClassName}>Filter by classification</span>
        <select
          className="min-h-[38px] max-w-full rounded-[7px] border border-border-input bg-surface px-2 text-small text-ink"
          value={classification}
          onChange={(event) =>
            onClassificationChange(
              event.target.value as CommunicationBalanceClassification | "all",
            )
          }
        >
          <option value="all">All classifications</option>
          {classifications.map((value) => (
            <option key={value} value={value}>
              {classificationLabels[value]}
            </option>
          ))}
        </select>
      </label>
      <label className="text-small text-ink-muted">
        <span className={screenReaderOnlyClassName}>Sort contacts by</span>
        <select
          className="min-h-[38px] max-w-full rounded-[7px] border border-border-input bg-surface px-2 text-small text-ink"
          value={sortKey}
          onChange={(event) =>
            onSortKeyChange(event.target.value as BalanceSortKey)
          }
        >
          <option value="text_volume">Total text volume</option>
          <option value="owner_share">Owner text share</option>
          <option value="recent_activity">Most recent activity</option>
        </select>
      </label>
      <label className="text-small text-ink-muted">
        <span className={screenReaderOnlyClassName}>Sort direction</span>
        <select
          className="min-h-[38px] rounded-[7px] border border-border-input bg-surface px-2 text-small text-ink"
          value={sortDirection}
          onChange={(event) =>
            onSortDirectionChange(event.target.value as SortDirection)
          }
        >
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </label>
    </div>
  );
}
