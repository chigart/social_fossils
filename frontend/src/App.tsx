import { useEffect, useState } from "react";
import {
  getChats,
  getContacts,
  getOverview,
  type ChatStatistics,
  type ContactStatistics,
  type OverviewStatistics,
} from "./api";
import { ChatsView } from "./components/ChatsView";
import { ContactsView } from "./components/ContactsView";
import { DashboardHeader } from "./components/DashboardHeader";
import { DashboardIntro } from "./components/DashboardIntro";
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
  const [chatSearch, setChatSearch] = useState("");
  const [contactSearch, setContactSearch] = useState("");
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

  useEffect(() => {
    void loadOverview();
    void loadChats();
    void loadContacts();
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
        <footer className="px-0 pt-[6px] pb-3 text-center text-caption text-ink-footer">
          Statistics are aggregated from imported data. Message contents are not shown.
        </footer>
      </div>
    </main>
  );
}
