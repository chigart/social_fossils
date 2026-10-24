import { useState } from "react";
import type {
  IdentityLinksResponse,
  PlatformIdentity,
} from "../api";
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

function identityLabel(identity: PlatformIdentity | undefined): string {
  if (!identity) return "Unknown identity";
  const contact = identity.contacts.find((item) => item.display_name) ??
    identity.contacts.find((item) => item.username);
  return contact?.display_name ??
    contact?.username ??
    `${identity.platform} ${identity.platform_user_id}`;
}

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
  const [firstIdentityId, setFirstIdentityId] = useState("");
  const [secondIdentityId, setSecondIdentityId] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const identities = identityLinks.data?.identities ?? [];
  const identityById = new Map(
    identities.map((identity) => [identity.identity_id, identity]),
  );
  const groups = new Map<number, PlatformIdentity[]>();
  for (const identity of identities) {
    if (identity.identity_group_id === null) continue;
    const group = groups.get(identity.identity_group_id) ?? [];
    group.push(identity);
    groups.set(identity.identity_group_id, group);
  }

  const performLink = async () => {
    const first = Number(firstIdentityId);
    const second = Number(secondIdentityId);
    if (!Number.isInteger(first) || !Number.isInteger(second) || first === second) {
      setActionError("Choose two different platform identities.");
      return;
    }
    setSaving(true);
    setActionError(null);
    setActionMessage(null);
    try {
      await onLink(first, second);
      setActionMessage("The platform identities are linked.");
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to link identities.",
      );
    } finally {
      setSaving(false);
    }
  };

  const performUnlink = async (identity: PlatformIdentity) => {
    setSaving(true);
    setActionError(null);
    setActionMessage(null);
    try {
      await onUnlink(identity.identity_id);
      setActionMessage(`${identityLabel(identity)} was unlinked.`);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to unlink identity.",
      );
    } finally {
      setSaving(false);
    }
  };

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
                  {identities.map((identity) => (
                    <option
                      key={identity.identity_id}
                      value={identity.identity_id}
                    >
                      {identity.platform}: {identityLabel(identity)} (
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
                  {identities.map((identity) => (
                    <option
                      key={identity.identity_id}
                      value={identity.identity_id}
                    >
                      {identity.platform}: {identityLabel(identity)} (
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
            {groups.size === 0 ? (
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
                {[...groups.entries()].map(([groupId, members]) => (
                  <div
                    className="rounded-lg border border-border-muted bg-surface p-4"
                    key={groupId}
                  >
                    <p className="mb-2 text-label font-semibold text-ink-muted">
                      Linked person group {groupId}
                    </p>
                    <ul className="space-y-2">
                      {members.map((identity) => (
                        <li
                          className="flex flex-wrap items-center justify-between gap-2"
                          key={identity.identity_id}
                        >
                          <span className="text-small text-ink">
                            <strong>{identity.platform}</strong>:{" "}
                            {identityLabel(identity)}{" "}
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
                            Unlink {identityLabel(identity)}
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
            {identityLinks.data.contacts_without_identity.length === 0 ? (
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
                    {identityLinks.data.contacts_without_identity.map((contact) => (
                      <tr className={tableRowClassName} key={contact.contact_id}>
                        <th className={tableRowTitleClassName} scope="row">
                          {contact.display_name || contact.username || "Unnamed contact"}
                        </th>
                        <td className={tableCellClassName}>{contact.platform}</td>
                        <td className={tableCellClassName}>{contact.account_label}</td>
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
            {identityLinks.data.events.length === 0 ? (
              <p className="text-small text-ink-muted">
                Explicit link and unlink actions will be recorded here.
              </p>
            ) : (
              <ul className="space-y-2">
                {identityLinks.data.events.map((event) => (
                  <li
                    className="text-small text-ink-muted"
                    key={event.id}
                  >
                    {event.action === "linked" ? "Linked" : "Unlinked"}{" "}
                    {identityLabel(identityById.get(event.identity_id))}
                    {event.peer_identity_id !== null &&
                      ` and ${identityLabel(identityById.get(event.peer_identity_id))}`}
                    {" · "}
                    {event.source} · {new Date(event.occurred_at).toLocaleString()}
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
