import { useMemo, useState } from "react";
import {
  type ChatStatistics,
  type ChatSortBy,
  type CommunicationBalanceClassification,
  type CommunicationBalanceStatistics,
  type ContactStatistics,
  type ContactSortBy,
  type ForgottenContactsStatistics,
  type PaginatedItems,
} from "../api";
import {
  sortCommunicationBalanceContacts,
  type BalanceSortKey,
} from "../utils/communicationBalance";
import type { Resource, SortDirection } from "../types";

type ForgottenSortKey =
  | "ranking_score"
  | "display_name"
  | "days_since_last_communication";

function searchOptionIndex(
  options: { value: string; platforms: string[] }[] | undefined,
  value: string,
  platform: string,
): number {
  if (!value) return -1;
  if (platform && options) {
    return options
      .filter((option) => option.platforms.includes(platform))
      .findIndex((option) => option.value === value);
  }
  const numericValue = Number(value);
  if (Number.isInteger(numericValue)) return numericValue;
  return options?.findIndex((option) => option.value === value) ?? -1;
}

export function useDashboardFilters({
  chatScope,
  chats,
  contacts,
  balance,
  forgottenContacts,
}: {
  chatScope: "dm" | "group";
  chats: Resource<PaginatedItems<ChatStatistics>>;
  contacts: Resource<PaginatedItems<ContactStatistics>>;
  balance: Resource<CommunicationBalanceStatistics>;
  forgottenContacts: Resource<ForgottenContactsStatistics>;
}) {
  const [chatSearch, setChatSearch] = useState("");
  const [chatPlatformFilter, setChatPlatformFilter] = useState("");
  const [contactSearch, setContactSearch] = useState("");
  const [contactPlatformFilter, setContactPlatformFilter] = useState("");
  const [balanceSearch, setBalanceSearch] = useState("");
  const [balancePlatformFilter, setBalancePlatformFilter] = useState("");
  const [forgottenSearch, setForgottenSearch] = useState("");
  const [forgottenPlatformFilter, setForgottenPlatformFilter] = useState("");
  const [balanceClassification, setBalanceClassification] = useState<
    CommunicationBalanceClassification | "all"
  >("all");
  const [forgottenSortKey, setForgottenSortKey] =
    useState<ForgottenSortKey>("ranking_score");
  const [forgottenSortDirection, setForgottenSortDirection] =
    useState<SortDirection>("desc");
  const [balanceSortKey, setBalanceSortKey] =
    useState<BalanceSortKey>("text_volume");
  const [balanceSortDirection, setBalanceSortDirection] =
    useState<SortDirection>("desc");
  const [chatSortByScope, setChatSortByScope] = useState<
    Record<
      "dm" | "group",
      { key: ChatSortBy; direction: SortDirection }
    >
  >({
    dm: { key: "total_messages", direction: "desc" },
    group: { key: "total_messages", direction: "desc" },
  });
  const chatSort = chatSortByScope[chatScope];
  const [contactSort, setContactSort] = useState<{
    key: ContactSortBy;
    direction: SortDirection;
  }>({ key: "total_messages_sent", direction: "desc" });

  const changeChatSort = (key: ChatSortBy) => {
    setChatSortByScope((current) => ({
      ...current,
      [chatScope]: {
        key,
        direction:
          current[chatScope].key === key &&
          current[chatScope].direction === "asc"
            ? "desc"
            : "asc",
      },
    }));
  };

  const changeContactSort = (key: ContactSortBy) => {
    setContactSort((current) => ({
      key,
      direction:
        current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  };

  const visibleChats = useMemo(
    () =>
      (chats.data?.items ?? [])
        .filter((chat) =>
          (!chatPlatformFilter || chat.platform === chatPlatformFilter) &&
          (chatSearch === "" || String(chat.chat_id) === chatSearch),
        )
        .sort((left, right) => {
          let comparison: number;
          if (chatSort.key === "title") {
            comparison = (left.title ?? "").localeCompare(right.title ?? "");
          } else if (chatSort.key === "total_messages") {
            comparison = left.total_messages - right.total_messages;
          } else if (chatSort.key === "text_length") {
            comparison = left.text_length - right.text_length;
          } else if (chatSort.key === "average_response_seconds") {
            if (left.average_response_seconds === null) {
              return right.average_response_seconds === null
                ? 0
                : 1;
            }
            if (right.average_response_seconds === null) return -1;
            comparison =
              left.average_response_seconds - right.average_response_seconds;
          } else if (chatSort.key === "distinct_identified_senders") {
            comparison =
              left.distinct_identified_senders -
              right.distinct_identified_senders;
          } else {
            const leftTimestamp =
              chatSort.key === "earliest_message_timestamp"
                ? left.earliest_message_timestamp
                : left.latest_message_timestamp;
            const rightTimestamp =
              chatSort.key === "earliest_message_timestamp"
                ? right.earliest_message_timestamp
                : right.latest_message_timestamp;
            if (leftTimestamp === null) {
              return rightTimestamp === null ? 0 : 1;
            }
            if (rightTimestamp === null) return -1;
            comparison =
              Date.parse(leftTimestamp) - Date.parse(rightTimestamp);
          }
          return chatSort.direction === "asc" ? comparison : -comparison;
        }),
    [chats.data?.items, chatSearch, chatPlatformFilter, chatSort],
  );

  const visibleContacts = useMemo(
    () => {
      const offset =
        ((contacts.data?.pagination.page ?? 1) - 1) *
        (contacts.data?.pagination.page_size ?? 0);
      const selectedIndex = searchOptionIndex(
        contacts.data?.options,
        contactSearch,
        contactPlatformFilter,
      );
      return (contacts.data?.items ?? [])
        .map((contact, index) => ({ contact, index: offset + index }))
        .filter(
          ({ contact }) =>
            contact.display_name?.trim() || contact.platform_user_ids.length > 0,
        )
        .filter(({ contact }) =>
          !contactPlatformFilter ||
          contact.platforms.includes(contactPlatformFilter),
        )
        .filter(({ index }) =>
          selectedIndex < 0 || index === selectedIndex,
        )
        .map(({ contact }) => contact)
        .sort((left, right) => {
          const comparison = left[contactSort.key] - right[contactSort.key];
          return contactSort.direction === "asc" ? comparison : -comparison;
        });
    },
    [contacts.data, contactSearch, contactPlatformFilter, contactSort],
  );

  const visibleBalanceContacts = useMemo(
    () => {
      const offset =
        ((balance.data?.pagination.page ?? 1) - 1) *
        (balance.data?.pagination.page_size ?? 0);
      const selectedIndex = searchOptionIndex(
        balance.data?.options,
        balanceSearch,
        balancePlatformFilter,
      );
      return sortCommunicationBalanceContacts(
        (balance.data?.contacts ?? [])
          .filter((_, index) =>
            selectedIndex < 0 || offset + index === selectedIndex,
          )
          .filter(
            (contact) =>
              (!balancePlatformFilter ||
                contact.platforms.includes(balancePlatformFilter)) &&
              (balanceClassification === "all" ||
                contact.classification === balanceClassification),
          ),
        balanceSortKey,
        balanceSortDirection,
      );
    },
    [
      balance.data,
      balanceSearch,
      balancePlatformFilter,
      balanceClassification,
      balanceSortKey,
      balanceSortDirection,
    ],
  );

  const visibleForgottenContacts = useMemo(
    () => {
      const offset =
        ((forgottenContacts.data?.pagination.page ?? 1) - 1) *
        (forgottenContacts.data?.pagination.page_size ?? 0);
      const selectedIndex = searchOptionIndex(
        forgottenContacts.data?.options,
        forgottenSearch,
        forgottenPlatformFilter,
      );
      return (forgottenContacts.data?.contacts ?? [])
        .filter((contact) =>
          !forgottenPlatformFilter ||
          contact.platforms.includes(forgottenPlatformFilter),
        )
        .filter((_, index) =>
          selectedIndex < 0 || offset + index === selectedIndex,
        )
        .sort((left, right) => {
          const direction = forgottenSortDirection === "asc" ? 1 : -1;

          if (forgottenSortKey === "display_name") {
            return (
              direction *
              (left.display_name ?? "").localeCompare(right.display_name ?? "")
            );
          }

          const leftValue = forgottenSortKey === "days_since_last_communication"
            ? left.days_since_last_communication
            : left.ranking_score;
          const rightValue = forgottenSortKey === "days_since_last_communication"
            ? right.days_since_last_communication
            : right.ranking_score;

          if (leftValue === null) return rightValue === null ? 0 : 1;
          if (rightValue === null) return -1;

          return direction * (leftValue - rightValue);
        });
    },
    [
      forgottenContacts.data,
      forgottenSearch,
      forgottenPlatformFilter,
      forgottenSortDirection,
      forgottenSortKey,
    ],
  );

  return {
    chatSearch,
    setChatSearch,
    chatPlatformFilter,
    setChatPlatformFilter,
    contactSearch,
    setContactSearch,
    contactPlatformFilter,
    setContactPlatformFilter,
    balanceSearch,
    setBalanceSearch,
    balancePlatformFilter,
    setBalancePlatformFilter,
    forgottenSearch,
    setForgottenSearch,
    forgottenPlatformFilter,
    setForgottenPlatformFilter,
    balanceClassification,
    setBalanceClassification,
    forgottenSortKey,
    setForgottenSortKey,
    forgottenSortDirection,
    setForgottenSortDirection,
    balanceSortKey,
    setBalanceSortKey,
    balanceSortDirection,
    setBalanceSortDirection,
    chatSort,
    changeChatSort,
    contactSort,
    changeContactSort,
    visibleChats,
    visibleContacts,
    visibleBalanceContacts,
    visibleForgottenContacts,
  };
}
