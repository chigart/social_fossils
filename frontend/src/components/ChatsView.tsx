import type { ChatStatistics } from "../api";
import { formatDate, formatNumber } from "../format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  screenReaderOnlyClassName,
  searchInputClassName,
  searchLabelClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
  tableCellClassName,
  tableClassName,
  tableContainerClassName,
  tableHeadClassName,
  tableHeaderClassName,
  tableRowClassName,
  tableRowTitleClassName,
  numericTableCellClassName,
} from "../styles";
import type { Resource, SortDirection } from "../types";
import { PlatformAccountBadge } from "./PlatformAccountBadge";
import { LoadingMessage, SectionError, SortButton } from "./Feedback";

type ChatSort = {
  key: "title" | "total_messages";
  direction: SortDirection;
};

export function ChatsView({
  chats,
  visibleChats,
  search,
  onSearchChange,
  sort,
  onSort,
  hasImportedAccounts,
  onRetry,
}: {
  chats: Resource<ChatStatistics[]>;
  visibleChats: ChatStatistics[];
  search: string;
  onSearchChange: (value: string) => void;
  sort: ChatSort;
  onSort: (key: ChatSort["key"]) => void;
  hasImportedAccounts: boolean;
  onRetry: () => void;
}) {
  return (
    <section
      id="chats"
      className={sectionClassName}
      aria-labelledby="chats-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>CONVERSATIONS</p>
          <h2 id="chats-title" className={sectionTitleClassName}>Chats</h2>
        </div>
        {chats.data && (
          <label className={searchLabelClassName}>
            <span className={screenReaderOnlyClassName}>Search chats by title</span>
            <input
              className={searchInputClassName}
              type="search"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search chat titles"
            />
          </label>
        )}
      </div>
      {chats.loading && chats.data === null && <LoadingMessage />}
      {chats.error && <SectionError message={chats.error} onRetry={onRetry} />}
      {chats.data && chats.data.length === 0 && (
        <div className={`${emptyStateClassName} p-[23px]`}>
          <h3 className={emptyStateTitleClassName}>No chats available</h3>
          <p className={emptyStateTextClassName}>
            {hasImportedAccounts
              ? "No chats were included in the imported account data."
              : "Import a Telegram export to see chat statistics."}
          </p>
        </div>
      )}
      {chats.data && chats.data.length > 0 && visibleChats.length === 0 && (
        <div className={`${emptyStateClassName} p-4`}>
          <p className={emptyStateTextClassName}>
            No chats match “{search}”. Try a different title.
          </p>
        </div>
      )}
      {chats.data && visibleChats.length > 0 && (
        <div className={tableContainerClassName}>
          <table className={tableClassName}>
            <thead className={tableHeadClassName}>
              <tr>
                <th className={tableHeaderClassName} scope="col">
                  <SortButton
                    label="Chat title"
                    active={sort.key === "title"}
                    direction={sort.direction}
                    onClick={() => onSort("title")}
                  />
                </th>
                <th className={tableHeaderClassName} scope="col">Type</th>
                <th className={tableHeaderClassName} scope="col">Account</th>
                <th className={tableHeaderClassName} scope="col">
                  <SortButton
                    label="Messages"
                    active={sort.key === "total_messages"}
                    direction={sort.direction}
                    onClick={() => onSort("total_messages")}
                  />
                </th>
                <th className={tableHeaderClassName} scope="col">Ordinary</th>
                <th className={tableHeaderClassName} scope="col">Service</th>
                <th className={tableHeaderClassName} scope="col">Senders</th>
                <th className={tableHeaderClassName} scope="col">First message</th>
                <th className={tableHeaderClassName} scope="col">Latest message</th>
              </tr>
            </thead>
            <tbody>
              {visibleChats.map((chat) => (
                <tr className={tableRowClassName} key={chat.chat_id}>
                  <th className={tableRowTitleClassName} scope="row">
                    {chat.title || "Untitled chat"}
                  </th>
                  <td className={tableCellClassName}>
                    <span className="inline-block whitespace-nowrap rounded bg-surface-tag px-[7px] py-1 text-label font-semibold text-ink-tag">
                      {chat.chat_type}
                    </span>
                  </td>
                  <td className={tableCellClassName}>
                    <PlatformAccountBadge
                      platform="telegram"
                      accountLabel={chat.source_account_label}
                    />
                  </td>
                  <td className={numericTableCellClassName}>
                    {formatNumber(chat.total_messages)}
                  </td>
                  <td className={numericTableCellClassName}>
                    {formatNumber(chat.ordinary_messages)}
                  </td>
                  <td className={numericTableCellClassName}>
                    {formatNumber(chat.service_messages)}
                  </td>
                  <td className={numericTableCellClassName}>
                    {formatNumber(chat.distinct_identified_senders)}
                  </td>
                  <td className={tableCellClassName}>
                    {formatDate(chat.earliest_message_timestamp)}
                  </td>
                  <td className={tableCellClassName}>
                    {formatDate(chat.latest_message_timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
