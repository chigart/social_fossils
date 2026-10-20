import type {
  CommunicationBalanceClassification,
  CommunicationBalanceContact,
} from "../api";
import type { SortDirection } from "../types";

export type BalanceSortKey = "text_volume" | "owner_share" | "recent_activity";

export const classificationLabels: Record<
  CommunicationBalanceClassification,
  string
> = {
  balanced: "Balanced",
  mostly_owner: "Mostly owner",
  mostly_contact: "Mostly contact",
  strongly_owner: "Strongly owner",
  strongly_contact: "Strongly contact",
  insufficient_data: "Insufficient data",
};

export const classifications = Object.keys(
  classificationLabels,
) as CommunicationBalanceClassification[];

function compareNullable(
  left: number | null,
  right: number | null,
  direction: SortDirection,
) {
  if (left === null || right === null) {
    if (left === right) return 0;
    return left === null ? 1 : -1;
  }
  const comparison = left - right;
  return direction === "asc" ? comparison : -comparison;
}

function compareDates(
  left: string | null,
  right: string | null,
  direction: SortDirection,
) {
  if (left === null || right === null) {
    if (left === right) return 0;
    return left === null ? 1 : -1;
  }
  const leftTime = new Date(left).getTime();
  const rightTime = new Date(right).getTime();
  if (Number.isNaN(leftTime) || Number.isNaN(rightTime)) {
    if (Number.isNaN(leftTime) === Number.isNaN(rightTime)) return 0;
    return Number.isNaN(leftTime) ? 1 : -1;
  }
  const comparison = leftTime - rightTime;
  return direction === "asc" ? comparison : -comparison;
}

function compareContacts(
  left: CommunicationBalanceContact,
  right: CommunicationBalanceContact,
  sortKey: BalanceSortKey,
  direction: SortDirection,
) {
  let comparison = 0;
  if (sortKey === "owner_share") {
    comparison = compareNullable(
      left.owner_share_percentage,
      right.owner_share_percentage,
      direction,
    );
  } else if (sortKey === "recent_activity") {
    comparison = compareDates(left.last_message_at, right.last_message_at, direction);
  } else {
    comparison = compareNullable(
      left.total_text_length,
      right.total_text_length,
      direction,
    );
  }
  if (comparison !== 0) return comparison;
  return (left.display_name ?? "").localeCompare(right.display_name ?? "");
}

export function sortCommunicationBalanceContacts(
  contacts: CommunicationBalanceContact[],
  sortKey: BalanceSortKey,
  direction: SortDirection,
) {
  return [...contacts].sort((left, right) =>
    compareContacts(left, right, sortKey, direction),
  );
}
