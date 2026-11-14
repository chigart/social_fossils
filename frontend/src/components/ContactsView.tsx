import type {
  ContactSortBy,
  ContactStatistics,
  PaginatedItems,
} from "../api";
import { formatNumber } from "../utils/format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  numericTableCellClassName,
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

export function ContactsView({
  contacts,
  visibleContacts,
  search,
  searchOptions,
  onSearchChange,
  sort,
  onSort,
  hasMessages,
  onRetry,
  onPageChange,
}: {
  contacts: Resource<PaginatedItems<ContactStatistics>>;
  visibleContacts: ContactStatistics[];
  search: string;
  searchOptions: SearchPickerOption[];
  onSearchChange: (value: string) => void;
  sort: { key: ContactSortBy; direction: SortDirection };
  onSort: (key: ContactSortBy) => void;
  hasMessages: boolean;
  onRetry: () => void;
  onPageChange: (page: number) => void;
}) {
  return (
    <section
      id="contacts"
      className={sectionClassName}
      aria-labelledby="contacts-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>INCOMING COMMUNICATION</p>
          <h2 id="contacts-title" className={sectionTitleClassName}>
            Contacts &amp; senders
          </h2>
        </div>
        {contacts.data && contacts.data.items.length > 0 && (
          <SearchPicker
            label="Choose a contact"
            value={search}
            options={searchOptions}
            onChange={onSearchChange}
            placeholder="All contacts"
            searchPlaceholder="Search contact name or ID"
            allLabel="All contacts"
            emptyMessage="No contacts match these filters."
          />
        )}
      </div>
      <p className="-mt-[9px] mb-4 text-small leading-[1.5] text-ink-muted">
        Explicitly linked identities are combined across messaging accounts.
        Unlinked identities remain separate; display names are never used to
        merge people.
      </p>
      {contacts.loading && contacts.data === null && <LoadingMessage />}
      {contacts.error && (
        <SectionError message={contacts.error} onRetry={onRetry} />
      )}
      {contacts.data && contacts.data.items.length === 0 && (
        <div className={`${emptyStateClassName} p-[23px]`}>
          <h3 className={emptyStateTitleClassName}>
            No contact communication available
          </h3>
          <p className={emptyStateTextClassName}>
            {hasMessages
              ? "There are no incoming sender groups in the available analytics."
              : "Import messages to see incoming communication by sender."}
          </p>
        </div>
      )}
      {contacts.data && contacts.data.items.length > 0 && visibleContacts.length === 0 && (
        <div className={`${emptyStateClassName} p-4`}>
          <p className={emptyStateTextClassName}>
            No contacts match the selected contact.
          </p>
        </div>
      )}
      {contacts.data && visibleContacts.length > 0 && (
        <>
          <PaginationControls
            pagination={contacts.data.pagination}
            onPageChange={onPageChange}
            label="Contacts pagination above table"
          />
          <div className={tableContainerClassName}>
            <table className={tableClassName}>
              <thead className={tableHeadClassName}>
                <tr>
                  <th className={tableHeaderClassName} scope="col">Contact / sender</th>
                  <th className={tableHeaderClassName} scope="col">User ID</th>
                  <th className={tableHeaderClassName} scope="col">Accounts</th>
                  <th className={tableHeaderClassName} scope="col">
                    <SortButton
                      label="DM messages"
                      active={sort.key === "personal_chat_messages_sent"}
                      direction={sort.direction}
                      onClick={() => onSort("personal_chat_messages_sent")}
                    />
                  </th>
                  <th className={tableHeaderClassName} scope="col">
                    <SortButton
                      label="Group messages"
                      active={sort.key === "group_chat_messages_sent"}
                      direction={sort.direction}
                      onClick={() => onSort("group_chat_messages_sent")}
                    />
                  </th>
                  <th className={tableHeaderClassName} scope="col">
                    <SortButton
                      label="Messages sent"
                      active={sort.key === "total_messages_sent"}
                      direction={sort.direction}
                      onClick={() => onSort("total_messages_sent")}
                    />
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibleContacts.map((contact, index) => (
                  <tr
                    className={tableRowClassName}
                    key={`${contact.identity_group_id ?? contact.canonical_identity_id ?? contact.source_contact_ids[0] ?? contact.account_id ?? "sources"}-${index}`}
                  >
                    <th className={tableRowTitleClassName} scope="row">
                      {contact.display_name?.trim() || "Unnamed contact"}
                    </th>
                    <td className={tableCellClassName}>
                      {contact.platform_user_ids.join(", ") || "—"}
                    </td>
                    <td className={tableCellClassName}>
                      {contact.source_accounts.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {contact.source_accounts.map(({ platform, label }, accountIndex) => (
                            <PlatformAccountBadge
                              key={`${platform}:${label}:${accountIndex}`}
                              platform={platform}
                              accountLabel={label}
                            />
                          ))}
                        </div>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(contact.personal_chat_messages_sent)}
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(contact.group_chat_messages_sent)}
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(contact.total_messages_sent)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {contacts.data && (
        <PaginationControls
          pagination={contacts.data.pagination}
          onPageChange={onPageChange}
          label="Contacts pagination below table"
        />
      )}
    </section>
  );
}
