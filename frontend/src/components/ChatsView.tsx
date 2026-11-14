import type { ChatSortBy, ChatStatistics, PaginatedItems } from "../api";
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
  navigationLinkClassName,
} from "../constants";
import type { Resource, SortDirection } from "../types";
import { PlatformAccountBadge } from "./PlatformAccountBadge";
import {
  LoadingMessage,
  PaginationControls,
  SectionError,
  SortButton,
} from "./Feedback";
import {
  PlatformFilterSelect,
  SearchPicker,
  type SearchPickerOption,
} from "./SearchPicker";
import { formatResponseTime } from "../utils/formatResponseTime";

export function ChatsView({
  chats,
  chatScope,
  visibleChats,
  search,
  platformFilter,
  searchOptions,
  onSearchChange,
  onPlatformFilterChange,
  sort,
  onSort,
  hasImportedAccounts,
  onRetry,
  onPageChange,
  onOpenChatInsights,
}: {
  chats: Resource<PaginatedItems<ChatStatistics>>;
  chatScope: "dm" | "group";
  visibleChats: ChatStatistics[];
  search: string;
  platformFilter: string;
  searchOptions: SearchPickerOption[];
  onSearchChange: (value: string) => void;
  onPlatformFilterChange: (value: string) => void;
  sort: { key: ChatSortBy; direction: SortDirection };
  onSort: (key: ChatSortBy) => void;
  hasImportedAccounts: boolean;
  onRetry: () => void;
  onPageChange: (page: number) => void;
  onOpenChatInsights: (chatId: number) => void;
}) {
  const title = chatScope === "dm" ? "DMs" : "Chats";
  const allLabel = chatScope === "dm" ? "All DMs" : "All chats";
  const emptyTitle = chatScope === "dm" ? "No DMs available" : "No chats available";
  return (
    <section
      id={chatScope === "dm" ? "dms" : "chats"}
      className={sectionClassName}
      aria-labelledby={`${chatScope === "dm" ? "dms" : "chats"}-title`}
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>CONVERSATIONS</p>
          <h2
            id={`${chatScope === "dm" ? "dms" : "chats"}-title`}
            className={sectionTitleClassName}
          >
            {title}
          </h2>
        </div>
        {chats.data &&
          (chats.data.items.length > 0 ||
            searchOptions.length > 0 ||
            platformFilter !== "") && (
          <div className="flex flex-wrap gap-2">
            <PlatformFilterSelect
              label="Filter chats by platform"
              value={platformFilter}
              options={searchOptions}
              onChange={onPlatformFilterChange}
            />
            <SearchPicker
              label="Choose a chat"
              value={search}
              platformFilter={platformFilter}
              options={searchOptions}
              onChange={onSearchChange}
              placeholder={allLabel}
              searchPlaceholder={`Search ${chatScope === "dm" ? "DM" : "chat"} title or ID`}
              allLabel={allLabel}
              emptyMessage="No chats match these filters."
            />
          </div>
        )}
      </div>
      {chats.loading && chats.data === null && <LoadingMessage />}
      {chats.error && <SectionError message={chats.error} onRetry={onRetry} />}
      {chats.data && chats.data.items.length === 0 && (
        <div className={`${emptyStateClassName} p-[23px]`}>
          <h3 className={emptyStateTitleClassName}>{emptyTitle}</h3>
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
            pagination={search
              ? { ...chats.data.pagination, page: 1, total: 1 }
              : chats.data.pagination}
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
                  <th className={tableHeaderClassName} scope="col">Account</th>
                  <th className={tableHeaderClassName} scope="col">
                    <SortButton
                      label="Text volume"
                      active={sort.key === "text_length"}
                      direction={sort.direction}
                      onClick={() => onSort("text_length")}
                    />
                  </th>
                  <th className={tableHeaderClassName} scope="col">
                    <SortButton
                      label="Messages"
                      active={sort.key === "total_messages"}
                      direction={sort.direction}
                      onClick={() => onSort("total_messages")}
                    />
                  </th>
                  {chatScope === "group" && (
                    <th className={tableHeaderClassName} scope="col">
                      <SortButton
                        label="Senders"
                        active={sort.key === "distinct_identified_senders"}
                        direction={sort.direction}
                        onClick={() => onSort("distinct_identified_senders")}
                      />
                    </th>
                  )}
                  <th className={tableHeaderClassName} scope="col">
                    <SortButton
                      label="First message"
                      active={sort.key === "earliest_message_timestamp"}
                      direction={sort.direction}
                      onClick={() => onSort("earliest_message_timestamp")}
                    />
                  </th>
                  <th className={tableHeaderClassName} scope="col">
                    <SortButton
                      label="Latest message"
                      active={sort.key === "latest_message_timestamp"}
                      direction={sort.direction}
                      onClick={() => onSort("latest_message_timestamp")}
                    />
                  </th>
                  {chatScope === "dm" && (
                    <th className={tableHeaderClassName} scope="col">
                      <SortButton
                        label="Average time to reply"
                        active={sort.key === "average_response_seconds"}
                        direction={sort.direction}
                        onClick={() => onSort("average_response_seconds")}
                      />
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {visibleChats.map((chat) => (
                  <tr className={tableRowClassName} key={chat.chat_id}>
                    <th className={tableRowTitleClassName} scope="row">
                      <button
                        type="button"
                        className={`${navigationLinkClassName} cursor-pointer border-0 bg-transparent p-0 text-left font-[inherit]`}
                        onClick={() => onOpenChatInsights(chat.chat_id)}
                      >
                        {chat.title || "Untitled chat"}
                      </button>
                    </th>
                    <td className={tableCellClassName}>
                      <PlatformAccountBadge
                        platform={chat.platform}
                        accountLabel={chat.source_account_label}
                      />
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(chat.text_length)}
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(chat.total_messages)}
                    </td>
                    {chatScope === "group" && (
                      <td className={numericTableCellClassName}>
                        {formatNumber(chat.distinct_identified_senders)}
                      </td>
                    )}
                    <td className={tableCellClassName}>
                      {formatDate(chat.earliest_message_timestamp)}
                    </td>
                    <td className={tableCellClassName}>
                      {formatDate(chat.latest_message_timestamp)}
                    </td>
                    {chatScope === "dm" && (
                      <td className={tableCellClassName}>
                        {formatResponseTime(chat.average_response_seconds)}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {chats.data && (
        <PaginationControls
          pagination={search
            ? { ...chats.data.pagination, page: 1, total: 1 }
            : chats.data.pagination}
          onPageChange={onPageChange}
          label="Chats pagination below table"
        />
      )}
    </section>
  );
}
