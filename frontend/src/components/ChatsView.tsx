import type { ChatStatistics, PaginatedItems } from "../api";
import { formatDate, formatNumber } from "../utils/format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
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
} from "../constants";
import type { Resource, SortDirection } from "../types";
import { PlatformAccountBadge } from "./PlatformAccountBadge";
import {
  LoadingMessage,
  PaginationControls,
  SectionError,
  SortButton,
} from "./Feedback";
import { SearchPicker, type SearchPickerOption } from "./SearchPicker";

export function ChatsView({
  chats,
  visibleChats,
  search,
  searchOptions,
  onSearchChange,
  sort,
  onSort,
  hasImportedAccounts,
  onRetry,
  onPageChange,
}: {
  chats: Resource<PaginatedItems<ChatStatistics>>;
  visibleChats: ChatStatistics[];
  search: string;
  searchOptions: SearchPickerOption[];
  onSearchChange: (value: string) => void;
  sort: { key: "title" | "total_messages"; direction: SortDirection };
  onSort: (key: "title" | "total_messages") => void;
  hasImportedAccounts: boolean;
  onRetry: () => void;
  onPageChange: (page: number) => void;
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
        {chats.data && chats.data.items.length > 0 && (
          <SearchPicker
            label="Choose a chat"
            value={search}
            options={searchOptions}
            onChange={onSearchChange}
            placeholder="All chats"
            searchPlaceholder="Search chat title or ID"
            allLabel="All chats"
            emptyMessage="No chats match these filters."
          />
        )}
      </div>
      {chats.loading && chats.data === null && <LoadingMessage />}
      {chats.error && <SectionError message={chats.error} onRetry={onRetry} />}
      {chats.data && chats.data.items.length === 0 && (
        <div className={`${emptyStateClassName} p-[23px]`}>
          <h3 className={emptyStateTitleClassName}>No chats available</h3>
          <p className={emptyStateTextClassName}>
            {hasImportedAccounts
              ? "No chats were included in the imported account data."
              : "Import a messaging export to see chat statistics."}
          </p>
        </div>
      )}
      {chats.data && chats.data.items.length > 0 && visibleChats.length === 0 && (
        <div className={`${emptyStateClassName} p-4`}>
          <p className={emptyStateTextClassName}>
            No chats match the selected chat.
          </p>
        </div>
      )}
      {chats.data && visibleChats.length > 0 && (
        <>
          <PaginationControls
            pagination={chats.data.pagination}
            onPageChange={onPageChange}
            label="Chats pagination above table"
          />
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
                        platform={chat.platform}
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
        </>
      )}
      {chats.data && (
        <PaginationControls
          pagination={chats.data.pagination}
          onPageChange={onPageChange}
          label="Chats pagination below table"
        />
      )}
    </section>
  );
}
