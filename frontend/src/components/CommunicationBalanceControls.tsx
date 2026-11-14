import type { CommunicationBalanceClassification } from "../api";
import {
  communicationBalanceClassificationLabels,
  communicationBalanceClassifications,
} from "../constants";
import {
  type BalanceSortKey,
} from "../utils/communicationBalance";
import { screenReaderOnlyClassName } from "../constants";
import type { SortDirection } from "../types";
import {
  PlatformFilterSelect,
  SearchPicker,
  type SearchPickerOption,
} from "./SearchPicker";

export function CommunicationBalanceControls({
  search,
  platformFilter,
  onSearchChange,
  onPlatformFilterChange,
  searchOptions,
  classification,
  onClassificationChange,
  sortKey,
  sortDirection,
  onSortKeyChange,
  onSortDirectionChange,
}: {
  search: string;
  platformFilter: string;
  onSearchChange: (value: string) => void;
  onPlatformFilterChange: (value: string) => void;
  searchOptions: SearchPickerOption[];
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
      <PlatformFilterSelect
        label="Filter balance contacts by platform"
        value={platformFilter}
        options={searchOptions}
        onChange={onPlatformFilterChange}
      />
      <SearchPicker
        label="Choose a balance contact"
        value={search}
        platformFilter={platformFilter}
        options={searchOptions}
        onChange={onSearchChange}
        placeholder="All contacts"
        searchPlaceholder="Search contact name or ID"
        allLabel="All contacts"
        emptyMessage="No contacts match these filters."
      />
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
          {communicationBalanceClassifications.map((value) => (
            <option key={value} value={value}>
              {communicationBalanceClassificationLabels[value]}
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
