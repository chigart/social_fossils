import { useMemo, useState } from "react";
import {
  type ChatStatistics,
  type CommunicationBalanceClassification,
  type CommunicationBalanceStatistics,
  type ContactStatistics,
  type ForgottenContactsStatistics,
} from "../api";
import {
  sortCommunicationBalanceContacts,
  type BalanceSortKey,
} from "../components/communicationBalanceUtils";
import type { Resource, SortDirection } from "../types";

type ForgottenSortKey =
  | "ranking_score"
  | "display_name"
  | "days_since_last_communication";

type ChatSortKey = "title" | "total_messages";

export function useDashboardFilters({
  chats,
  contacts,
  balance,
  forgottenContacts,
}: {
  chats: Resource<ChatStatistics[]>;
  contacts: Resource<ContactStatistics[]>;
  balance: Resource<CommunicationBalanceStatistics>;
  forgottenContacts: Resource<ForgottenContactsStatistics>;
}) {
  const [chatSearch, setChatSearch] = useState("");
  const [contactSearch, setContactSearch] = useState("");
  const [balanceSearch, setBalanceSearch] = useState("");
  const [forgottenSearch, setForgottenSearch] = useState("");
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
  const [chatSort, setChatSort] = useState<{
    key: ChatSortKey;
    direction: SortDirection;
  }>({ key: "total_messages", direction: "desc" });
  const [contactSortDirection, setContactSortDirection] =
    useState<SortDirection>("desc");

  const changeChatSort = (key: ChatSortKey) => {
    setChatSort((current) => ({
      key,
      direction:
        current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  };

  const visibleChats = useMemo(
    () =>
      (chats.data ?? [])
        .filter((chat) => chatSearch === "" || String(chat.chat_id) === chatSearch)
        .sort((left, right) => {
          const comparison =
            chatSort.key === "title"
              ? (left.title ?? "").localeCompare(right.title ?? "")
              : left.total_messages - right.total_messages;
          return chatSort.direction === "asc" ? comparison : -comparison;
        }),
    [chats.data, chatSearch, chatSort],
  );

  const visibleContacts = useMemo(
    () =>
      (contacts.data ?? [])
        .map((contact, index) => ({ contact, index }))
        .filter(
          ({ contact }) =>
            contact.display_name?.trim() || contact.platform_user_ids.length > 0,
        )
        .filter(({ index }) =>
          contactSearch === "" || String(index) === contactSearch,
        )
        .map(({ contact }) => contact)
        .sort(
          (left, right) =>
            (contactSortDirection === "asc" ? 1 : -1) *
            (left.total_messages_sent - right.total_messages_sent),
        ),
    [contacts.data, contactSearch, contactSortDirection],
  );

  const visibleBalanceContacts = useMemo(
    () =>
      sortCommunicationBalanceContacts(
        (balance.data?.contacts ?? [])
          .filter((_, index) =>
            balanceSearch === "" || String(index) === balanceSearch,
          )
          .filter(
            (contact) =>
              balanceClassification === "all" ||
              contact.classification === balanceClassification,
          ),
        balanceSortKey,
        balanceSortDirection,
      ),
    [
      balance.data,
      balanceSearch,
      balanceClassification,
      balanceSortKey,
      balanceSortDirection,
    ],
  );

  const visibleForgottenContacts = useMemo(
    () =>
      (forgottenContacts.data?.contacts ?? [])
        .filter((_, index) =>
          forgottenSearch === "" || String(index) === forgottenSearch,
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
        }),
    [
      forgottenContacts.data,
      forgottenSearch,
      forgottenSortDirection,
      forgottenSortKey,
    ],
  );

  return {
    chatSearch,
    setChatSearch,
    contactSearch,
    setContactSearch,
    balanceSearch,
    setBalanceSearch,
    forgottenSearch,
    setForgottenSearch,
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
    contactSortDirection,
    setContactSortDirection,
    visibleChats,
    visibleContacts,
    visibleBalanceContacts,
    visibleForgottenContacts,
  };
}
