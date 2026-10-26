import type { ContactStatistics } from "../api";
import { formatNumber } from "../format";
import { formatPlatformAccountLabel } from "../platforms";
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
} from "../styles";
import type { Resource, SortDirection } from "../types";
import { LoadingMessage, SectionError, SortButton } from "./Feedback";
import { SearchPicker } from "./SearchPicker";

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
          <SearchPicker
            label="Choose a contact"
            value={search}
            options={contacts.data
              .map((contact, index) => ({ contact, index }))
              .filter(({ contact }) =>
                contact.display_name?.trim() || contact.platform_user_ids.length > 0
              )
              .map(({ contact, index }) => ({
                value: String(index),
                label: contact.display_name?.trim() || "Unnamed contact",
                platforms: contact.platforms,
                searchTerms: [
                  ...contact.platform_user_ids,
                  ...contact.source_account_labels,
                ],
              }))}
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
            No contacts match the selected contact.
          </p>
        </div>
      )}
      {contacts.data && visibleContacts.length > 0 && (
        <div className={tableContainerClassName}>
          <table className={tableClassName}>
            <thead className={tableHeadClassName}>
              <tr>
                <th className={tableHeaderClassName} scope="col">Contact / sender</th>
                <th className={tableHeaderClassName} scope="col">Accounts</th>
                <th className={tableHeaderClassName} scope="col">
                  <SortButton
                    label="Messages sent"
                    active
                    direction={sortDirection}
                    onClick={onSort}
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
                    {contact.source_accounts
                      .map(({ platform, label }) =>
                        formatPlatformAccountLabel(platform, label),
                      )
                      .join(", ") || "—"}
                  </td>
                  <td className={numericTableCellClassName}>
                    {formatNumber(contact.total_messages_sent)}
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
