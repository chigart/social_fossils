import { useEffect, useState } from "react";
import {
  getChats,
  getCommunicationBalance,
  getContacts,
  getForgottenContacts,
  getOverview,
  type ChatStatistics,
  type CommunicationBalanceClassification,
  type CommunicationBalanceStatistics,
  type ContactStatistics,
  type ForgottenContact,
  type ForgottenContactsStatistics,
  type OverviewStatistics,
} from "./api";
import { ChatsView } from "./components/ChatsView";
import {
  CommunicationBalanceView,
  sortCommunicationBalanceContacts,
  type BalanceSortKey,
} from "./components/CommunicationBalanceView";
import { ContactsView } from "./components/ContactsView";
import { DashboardHeader } from "./components/DashboardHeader";
import { DashboardIntro } from "./components/DashboardIntro";
import { ForgottenContactsView } from "./components/ForgottenContactsView";
import { OverviewView } from "./components/OverviewView";
import type { Resource, SortDirection } from "./types";

function emptyResource<T>(): Resource<T> {
  return { data: null, error: null, loading: true };
}

export default function App() {
  const [overview, setOverview] =
    useState<Resource<OverviewStatistics>>(emptyResource);
  const [chats, setChats] = useState<Resource<ChatStatistics[]>>(emptyResource);
  const [contacts, setContacts] =
    useState<Resource<ContactStatistics[]>>(emptyResource);
  const [balance, setBalance] =
    useState<Resource<CommunicationBalanceStatistics>>(emptyResource);
  const [forgottenContacts, setForgottenContacts] =
    useState<Resource<ForgottenContactsStatistics>>(emptyResource);
  const [chatSearch, setChatSearch] = useState("");
  const [contactSearch, setContactSearch] = useState("");
  const [balanceSearch, setBalanceSearch] = useState("");
  const [forgottenSearch, setForgottenSearch] = useState("");
  const [balanceClassification, setBalanceClassification] = useState<
    CommunicationBalanceClassification | "all"
  >("all");
  const [forgottenSortKey, setForgottenSortKey] = useState<
    "ranking_score" | "display_name" | "days_since_last_communication"
  >("ranking_score");
  const [forgottenSortDirection, setForgottenSortDirection] =
    useState<SortDirection>("desc");
  const [balanceSortKey, setBalanceSortKey] =
    useState<BalanceSortKey>("text_volume");
  const [balanceSortDirection, setBalanceSortDirection] =
    useState<SortDirection>("desc");
  const [chatSort, setChatSort] = useState<{
    key: "title" | "total_messages";
    direction: SortDirection;
  }>({ key: "total_messages", direction: "desc" });
  const [contactSortDirection, setContactSortDirection] =
    useState<SortDirection>("desc");

  const loadOverview = async () => {
    setOverview((current) => ({ ...current, error: null, loading: true }));
    try {
      setOverview({ data: await getOverview(), error: null, loading: false });
    } catch (error) {
      setOverview((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load overview statistics.",
        loading: false,
      }));
    }
  };

  const loadChats = async () => {
    setChats((current) => ({ ...current, error: null, loading: true }));
    try {
      setChats({ data: await getChats(), error: null, loading: false });
    } catch (error) {
      setChats((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load chat statistics.",
        loading: false,
      }));
    }
  };

  const loadContacts = async () => {
    setContacts((current) => ({ ...current, error: null, loading: true }));
    try {
      setContacts({ data: await getContacts(), error: null, loading: false });
    } catch (error) {
      setContacts((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load contact statistics.",
        loading: false,
      }));
    }
  };

  const loadBalance = async () => {
    setBalance((current) => ({ ...current, error: null, loading: true }));
    try {
      setBalance({
        data: await getCommunicationBalance(),
        error: null,
        loading: false,
      });
    } catch (error) {
      setBalance((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load communication balance statistics.",
        loading: false,
      }));
    }
  };

  const loadForgottenContacts = async () => {
    setForgottenContacts((current) => ({ ...current, error: null, loading: true }));
    try {
      setForgottenContacts({
        data: await getForgottenContacts(),
        error: null,
        loading: false,
      });
    } catch (error) {
      setForgottenContacts((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Unable to load forgotten contacts.",
        loading: false,
      }));
    }
  };

  useEffect(() => {
    void loadOverview();
    void loadChats();
    void loadContacts();
    void loadBalance();
    void loadForgottenContacts();
  }, []);

  const changeChatSort = (key: "title" | "total_messages") => {
    setChatSort((current) => ({
      key,
      direction:
        current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  };

  const visibleChats = (chats.data ?? [])
    .filter((chat) =>
      (chat.title ?? "Untitled chat")
        .toLocaleLowerCase()
        .includes(chatSearch.trim().toLocaleLowerCase()),
    )
    .sort((left, right) => {
      const comparison =
        chatSort.key === "title"
          ? (left.title ?? "").localeCompare(right.title ?? "")
          : left.total_messages - right.total_messages;
      return chatSort.direction === "asc" ? comparison : -comparison;
    });

  const visibleContacts = (contacts.data ?? [])
    .filter((contact) =>
      (contact.display_name ?? "")
        .toLocaleLowerCase()
        .includes(contactSearch.trim().toLocaleLowerCase()),
    )
    .sort(
      (left, right) =>
        (contactSortDirection === "asc" ? 1 : -1) *
        (left.total_messages_sent - right.total_messages_sent),
    );

  const visibleBalanceContacts = sortCommunicationBalanceContacts(
    (balance.data?.contacts ?? [])
      .filter((contact) =>
        (contact.display_name ?? "")
          .toLocaleLowerCase()
          .includes(balanceSearch.trim().toLocaleLowerCase()),
      )
      .filter(
        (contact) =>
          balanceClassification === "all" ||
          contact.classification === balanceClassification,
      ),
    balanceSortKey,
    balanceSortDirection,
  );

  const visibleForgottenContacts = (forgottenContacts.data?.contacts ?? [])
    .filter((contact) =>
      (contact.display_name ?? "")
        .toLocaleLowerCase()
        .includes(forgottenSearch.trim().toLocaleLowerCase()),
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

  const noImportedData =
    overview.data?.total_imported_accounts === 0 &&
    overview.data.total_chats === 0;

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <DashboardHeader />
      <div className="mx-auto w-full max-w-[1200px] px-7 pt-[46px] pb-[30px] max-[820px]:pt-[34px] max-sm:px-[14px] max-sm:py-[25px]">
        <DashboardIntro />
        <OverviewView
          overview={overview}
          noImportedData={noImportedData}
          onRetry={() => void loadOverview()}
        />
        <ChatsView
          chats={chats}
          visibleChats={visibleChats}
          search={chatSearch}
          onSearchChange={setChatSearch}
          sort={chatSort}
          onSort={changeChatSort}
          hasImportedAccounts={
            (overview.data?.total_imported_accounts ?? 0) > 0
          }
          onRetry={() => void loadChats()}
        />
        <ContactsView
          contacts={contacts}
          visibleContacts={visibleContacts}
          search={contactSearch}
          onSearchChange={setContactSearch}
          sortDirection={contactSortDirection}
          onSort={() =>
            setContactSortDirection((direction) =>
              direction === "asc" ? "desc" : "asc",
            )
          }
          hasMessages={(overview.data?.total_messages ?? 0) > 0}
          onRetry={() => void loadContacts()}
        />
        <CommunicationBalanceView
          balance={balance}
          visibleContacts={visibleBalanceContacts}
          search={balanceSearch}
          onSearchChange={setBalanceSearch}
          classification={balanceClassification}
          onClassificationChange={setBalanceClassification}
          sortKey={balanceSortKey}
          sortDirection={balanceSortDirection}
          onSortKeyChange={setBalanceSortKey}
          onSortDirectionChange={setBalanceSortDirection}
          onRetry={() => void loadBalance()}
        />
        <ForgottenContactsView
          forgotten={forgottenContacts}
          noImportedData={noImportedData}
          visibleContacts={visibleForgottenContacts}
          search={forgottenSearch}
          onSearchChange={setForgottenSearch}
          sortKey={forgottenSortKey}
          sortDirection={forgottenSortDirection}
          onSortKeyChange={setForgottenSortKey}
          onSortDirectionChange={setForgottenSortDirection}
          onRetry={() => void loadForgottenContacts()}
        />
        <footer className="px-0 pt-[6px] pb-3 text-center text-caption text-ink-footer">
          Statistics are aggregated from imported data. Message contents are not shown.
        </footer>
      </div>
    </main>
  );
}
