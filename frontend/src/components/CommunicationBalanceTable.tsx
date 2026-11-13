import type { CommunicationBalanceContact } from "../api";
import { formatDate, formatNumber } from "../format";
import {
  numericTableCellClassName,
  screenReaderOnlyClassName,
  tableCellClassName,
  tableClassName,
  tableHeadClassName,
  tableHeaderClassName,
  tableRowClassName,
  tableRowTitleClassName,
} from "../styles";
import { classificationLabels } from "./communicationBalanceUtils";

function formatShare(value: number | null) {
  return value === null
    ? "—"
    : `${new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 1,
      }).format(value)}%`;
}

function TextShareComparison({ contact }: { contact: CommunicationBalanceContact }) {
  const hasShares =
    contact.total_text_length > 0 &&
    contact.owner_share_percentage !== null &&
    contact.contact_share_percentage !== null;

  if (!hasShares) {
    return (
      <div className="min-w-[190px] text-caption text-ink-muted">
        <p className="mb-1 m-0">
          Owner {formatShare(contact.owner_share_percentage)} · Contact{" "}
          {formatShare(contact.contact_share_percentage)}
        </p>
        <span>
          {contact.total_text_length === 0
            ? "No text volume to compare"
            : "Text share unavailable"}
        </span>
      </div>
    );
  }

  return (
    <div
      className="min-w-[190px]"
      role="img"
      aria-label={`Owner ${formatShare(contact.owner_share_percentage)}, contact ${formatShare(contact.contact_share_percentage)}`}
    >
      <div className="mb-1 flex justify-between gap-2 text-caption tabular-nums text-ink-muted">
        <span>Owner {formatShare(contact.owner_share_percentage)}</span>
        <span>Contact {formatShare(contact.contact_share_percentage)}</span>
      </div>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-surface-neutral">
        <span
          className="h-full bg-brand"
          style={{ width: `${contact.owner_share_percentage}%` }}
        />
        <span
          className="h-full bg-ink-neutral"
          style={{ width: `${contact.contact_share_percentage}%` }}
        />
      </div>
    </div>
  );
}

export function CommunicationBalanceTable({
  contacts,
}: {
  contacts: CommunicationBalanceContact[];
}) {
  return (
    <>
      <div
        className="w-full overflow-x-scroll rounded-lg border border-border-subtle max-sm:max-w-full focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-2"
        role="region"
        aria-label="Scrollable communication balance table"
        tabIndex={0}
      >
        <table className={`${tableClassName} min-w-[1050px]`}>
          <caption className={screenReaderOnlyClassName}>
            Text volume, shares, classifications, and activity dates by eligible
            contact
          </caption>
          <thead className={tableHeadClassName}>
            <tr>
              <th className={tableHeaderClassName} scope="col">Contact</th>
              <th className={tableHeaderClassName} scope="col">Total</th>
              <th className={tableHeaderClassName} scope="col">Owner</th>
              <th className={tableHeaderClassName} scope="col">Contact</th>
              <th className={tableHeaderClassName} scope="col">Share</th>
              <th className={tableHeaderClassName} scope="col">Balance</th>
              <th className={tableHeaderClassName} scope="col">First seen</th>
              <th className={tableHeaderClassName} scope="col">Last seen</th>
            </tr>
          </thead>
          <tbody>
            {contacts.map((contact) => {
              const insufficient =
                contact.classification === "insufficient_data";
              return (
                <tr
                  className={`${tableRowClassName} ${insufficient ? "bg-surface-muted" : ""}`}
                  key={`${contact.account_id}-${contact.contact_id}`}
                >
                  <th className={tableRowTitleClassName} scope="row">
                    {contact.display_name || "Unnamed contact"}
                  </th>
                  <td className={numericTableCellClassName}>
                    {formatNumber(contact.total_text_length)}
                  </td>
                  <td className={numericTableCellClassName}>
                    {formatNumber(contact.owner_text_length)}
                  </td>
                  <td className={numericTableCellClassName}>
                    {formatNumber(contact.contact_text_length)}
                  </td>
                  <td className={tableCellClassName}>
                    <TextShareComparison contact={contact} />
                  </td>
                  <td className={tableCellClassName}>
                    <span
                      className={`inline-block whitespace-nowrap rounded px-[7px] py-1 text-label font-semibold ${
                        insufficient
                          ? "border border-border-input bg-surface-neutral text-ink-neutral"
                          : "bg-surface-tag text-ink-tag"
                      }`}
                    >
                      {classificationLabels[contact.classification]}
                    </span>
                    {insufficient && (
                      <p className="mt-1 mb-0 max-w-[180px] text-caption text-ink-muted">
                        Less than 500 characters; treat as limited data.
                      </p>
                    )}
                  </td>
                  <td className={tableCellClassName}>
                    {formatDate(contact.first_message_at)}
                  </td>
                  <td className={tableCellClassName}>
                    {formatDate(contact.last_message_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
