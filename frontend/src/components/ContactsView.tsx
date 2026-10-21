import type { ContactStatistics } from "../api";
import { formatNumber } from "../format";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  numericTableCellClassName,
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
} from "../styles";
import type { Resource, SortDirection } from "../types";
import { LoadingMessage, SectionError, SortButton } from "./Feedback";

export function ContactsView({
  contacts,
  visibleContacts,
  search,
  onSearchChange,
  sortDirection,
  onSort,
  hasMessages,
  onRetry,
}: {
  contacts: Resource<ContactStatistics[]>;
  visibleContacts: ContactStatistics[];
  search: string;
  onSearchChange: (value: string) => void;
  sortDirection: SortDirection;
  onSort: () => void;
  hasMessages: boolean;
  onRetry: () => void;
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
        {contacts.data && contacts.data.length > 0 && (
          <label className={searchLabelClassName}>
            <span className={screenReaderOnlyClassName}>
              Search contacts by display name
            </span>
            <input
              className={searchInputClassName}
              type="search"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search display names"
            />
          </label>
        )}
      </div>
      <p className="-mt-[9px] mb-4 text-small leading-[1.5] text-ink-muted">
        Incoming messages grouped by sender ID. Unlinked senders are not matched to
        contacts by name.
      </p>
      {contacts.loading && contacts.data === null && <LoadingMessage />}
      {contacts.error && (
        <SectionError message={contacts.error} onRetry={onRetry} />
      )}
      {contacts.data && contacts.data.length === 0 && (
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
      {contacts.data && contacts.data.length > 0 && visibleContacts.length === 0 && (
        <div className={`${emptyStateClassName} p-4`}>
          <p className={emptyStateTextClassName}>
            No display names match “{search}”.
          </p>
        </div>
      )}
      {contacts.data && visibleContacts.length > 0 && (
        <div className={tableContainerClassName}>
          <table className={tableClassName}>
            <thead className={tableHeadClassName}>
              <tr>
                <th className={tableHeaderClassName} scope="col">Contact / sender</th>
                <th className={tableHeaderClassName} scope="col">Telegram user ID</th>
                <th className={tableHeaderClassName} scope="col">Accounts</th>
                <th className={tableHeaderClassName} scope="col">Link status</th>
                <th className={tableHeaderClassName} scope="col">
                  <SortButton
                    label="Messages sent"
                    active
                    direction={sortDirection}
                    onClick={onSort}
                  />
                </th>
                <th className={tableHeaderClassName} scope="col">Ordinary</th>
                <th className={tableHeaderClassName} scope="col">Service events</th>
              </tr>
            </thead>
            <tbody>
              {visibleContacts.map((contact, index) => {
                const status =
                  contact.contact_id !== null
                    ? "Known contact"
                    : contact.telegram_user_id === null
                      ? "Unknown sender"
                      : "Unlinked sender";

                return (
                  <tr
                    className={tableRowClassName}
                    key={`${contact.canonical_identity_id ?? contact.account_id ?? "sources"}-${contact.telegram_user_id ?? "unknown"}-${index}`}
                  >
                    <th className={tableRowTitleClassName} scope="row">
                      {contact.display_name ||
                        (contact.telegram_user_id
                          ? "Unnamed contact"
                          : "Unknown sender")}
                    </th>
                    <td className="max-w-[200px] break-words border-b border-border-muted px-[13px] py-3 align-middle font-mono text-caption text-ink-code last:border-b-0">
                      {contact.telegram_user_id ?? "—"}
                    </td>
                    <td className={tableCellClassName}>
                      {contact.source_account_labels.join(", ") || "—"}
                    </td>
                    <td className={tableCellClassName}>
                      <span
                        className={`inline-block whitespace-nowrap rounded px-[7px] py-1 text-label font-semibold ${contact.contact_id === null ? "bg-surface-neutral text-ink-neutral" : "bg-surface-tag text-ink-tag"}`}
                      >
                        {status}
                      </span>
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(contact.total_messages_sent)}
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(contact.ordinary_messages_sent)}
                    </td>
                    <td className={numericTableCellClassName}>
                      {formatNumber(contact.service_events_attributed)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
