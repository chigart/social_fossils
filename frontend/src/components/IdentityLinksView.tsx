import type { IdentityLinksResponse } from "../api";
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
} from "../styles";
import type { Resource } from "../types";
import { LoadingMessage, SectionError } from "./Feedback";
import { PlatformAccountBadge } from "./PlatformAccountBadge";
import { useIdentityLinks } from "./useIdentityLinks";

export function IdentityLinksView({
  identityLinks,
  onRetry,
  onLink,
  onUnlink,
}: {
  identityLinks: Resource<IdentityLinksResponse>;
  onRetry: () => void;
  onLink: (firstIdentityId: number, secondIdentityId: number) => Promise<void>;
  onUnlink: (identityId: number) => Promise<void>;
}) {
  const {
    firstIdentityId,
    setFirstIdentityId,
    secondIdentityId,
    setSecondIdentityId,
    saving,
    actionError,
    actionMessage,
    identities,
    identityOptions,
    linkedGroups,
    unidentifiedContacts,
    historyEvents,
    performLink,
    performUnlink,
  } = useIdentityLinks(identityLinks, onLink, onUnlink);

  return (
    <section
      className={sectionClassName}
      aria-labelledby="identity-links-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>OWNER-VERIFIED IDENTITY</p>
          <h2 id="identity-links-title" className={sectionTitleClassName}>
            Cross-platform identity links
          </h2>
        </div>
      </div>
      <p className="mb-5 text-small leading-[1.5] text-ink-muted">
        Link only identities you recognize as the same person. Names and
        usernames are shown for review but are never used to match identities
        automatically. Conflicting links must be removed before a new link can
        be created.
      </p>
      {identityLinks.loading && identityLinks.data === null && <LoadingMessage />}
      {identityLinks.error && (
        <SectionError message={identityLinks.error} onRetry={onRetry} />
      )}
      {actionError && (
        <p className="mb-3 rounded-md bg-surface-danger p-3 text-small text-ink-danger" role="alert">
          {actionError}
        </p>
      )}
      {actionMessage && (
        <p className="mb-3 rounded-md bg-surface-success p-3 text-small text-ink-success" role="status">
          {actionMessage}
        </p>
      )}
      {identityLinks.data && (
        <>
          <section className="mb-7 rounded-lg border border-border-muted bg-surface p-4">
            <h3 className="mb-3 text-subheading font-bold text-ink">
              Link two identities
            </h3>
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-caption font-semibold text-ink-subtle">
                First platform identity
                <select
                  className="rounded-md border border-border bg-surface px-3 py-2 text-small text-ink"
                  value={firstIdentityId}
                  onChange={(event) => setFirstIdentityId(event.target.value)}
                >
                  <option value="">Select identity</option>
                  {identityOptions.map(({ identity, label }) => (
                    <option
                      key={identity.identity_id}
                      value={identity.identity_id}
                    >
                      {identity.platform}: {label} (
                      {identity.platform_user_id})
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-caption font-semibold text-ink-subtle">
                Second platform identity
                <select
                  className="rounded-md border border-border bg-surface px-3 py-2 text-small text-ink"
                  value={secondIdentityId}
                  onChange={(event) => setSecondIdentityId(event.target.value)}
                >
                  <option value="">Select identity</option>
                  {identityOptions.map(({ identity, label }) => (
                    <option
                      key={identity.identity_id}
                      value={identity.identity_id}
                    >
                      {identity.platform}: {label} (
                      {identity.platform_user_id})
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="rounded-md bg-surface-brand px-4 py-2 text-small font-semibold text-brand-strong disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                disabled={saving || identities.length < 2}
                onClick={() => void performLink()}
              >
                Link identities
              </button>
            </div>
            {identities.length < 2 && (
              <p className="mt-3 text-caption text-ink-muted">
                Import at least two identifiable platform contacts to create a
                link.
              </p>
            )}
          </section>

          <section className="mb-7" aria-labelledby="linked-identities-title">
            <h3
              id="linked-identities-title"
              className="mb-3 text-subheading font-bold text-ink"
            >
              Current links
            </h3>
            {linkedGroups.length === 0 ? (
              <div className={`${emptyStateClassName} p-4`}>
                <h4 className={emptyStateTitleClassName}>
                  No cross-platform links yet
                </h4>
                <p className={emptyStateTextClassName}>
                  Platform identities remain separate until you link them
                  explicitly.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {linkedGroups.map(({ groupId, members }) => (
                  <div
                    className="rounded-lg border border-border-muted bg-surface p-4"
                    key={groupId}
                  >
                    <p className="mb-2 text-label font-semibold text-ink-muted">
                      Linked person group {groupId}
                    </p>
                    <ul className="space-y-2">
                      {members.map(({ identity, label }) => (
                        <li
                          className="flex flex-wrap items-center justify-between gap-2"
                          key={identity.identity_id}
                        >
                          <span className="text-small text-ink">
                            <strong>{identity.platform}</strong>:{" "}
                            {label}{" "}
                            <span className="font-mono text-caption text-ink-muted">
                              ({identity.platform_user_id})
                            </span>
                          </span>
                          <button
                            className="rounded-md border border-border px-3 py-1.5 text-caption font-semibold text-ink-subtle disabled:opacity-50"
                            type="button"
                            disabled={saving}
                            onClick={() => void performUnlink(identity)}
                          >
                            Unlink {label}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="mb-7" aria-labelledby="unidentified-contacts-title">
            <h3
              id="unidentified-contacts-title"
              className="mb-3 text-subheading font-bold text-ink"
            >
              Contacts without a platform identity
            </h3>
            {unidentifiedContacts.length === 0 ? (
              <p className="text-small text-ink-muted">
                All imported contacts currently have a platform identity.
              </p>
            ) : (
              <div className={tableContainerClassName}>
                <table className={tableClassName}>
                  <thead className={tableHeadClassName}>
                    <tr>
                      <th className={tableHeaderClassName} scope="col">Contact</th>
                      <th className={tableHeaderClassName} scope="col">Platform</th>
                      <th className={tableHeaderClassName} scope="col">Source account</th>
                      <th className={tableHeaderClassName} scope="col">Link status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {unidentifiedContacts.map(({ contact, label }) => (
                      <tr className={tableRowClassName} key={contact.contact_id}>
                        <th className={tableRowTitleClassName} scope="row">
                          {label}
                        </th>
                        <td className={tableCellClassName}>{contact.platform}</td>
                        <td className={tableCellClassName}>
                          <PlatformAccountBadge
                            platform={contact.platform}
                            accountLabel={contact.account_label}
                          />
                        </td>
                        <td className={tableCellClassName}>Not linkable: no reliable platform ID</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section aria-labelledby="identity-link-history-title">
            <h3
              id="identity-link-history-title"
              className="mb-3 text-subheading font-bold text-ink"
            >
              Link history
            </h3>
            {historyEvents.length === 0 ? (
              <p className="text-small text-ink-muted">
                Explicit link and unlink actions will be recorded here.
              </p>
            ) : (
              <ul className="space-y-2">
                {historyEvents.map((event) => (
                  <li
                    className="text-small text-ink-muted"
                    key={event.id}
                  >
                    {event.description}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </section>
  );
}
