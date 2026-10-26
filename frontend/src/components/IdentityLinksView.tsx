import type { IdentityLinksResponse } from "../api";
import {
  emptyStateClassName,
  emptyStateTextClassName,
  emptyStateTitleClassName,
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../styles";
import type { Resource } from "../types";
import { Button } from "./Button";
import { LoadingMessage, SectionError } from "./Feedback";
import { SearchPicker } from "./SearchPicker";
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
    identityOptions,
    canLink,
    suggestedLinks,
    linkedGroups,
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
          <p className={sectionEyebrowClassName}>OWNER-VERIFIED IDENTITIES</p>
          <h2 id="identity-links-title" className={sectionTitleClassName}>
            Identity links
          </h2>
        </div>
      </div>
      <p className="mb-5 text-small leading-[1.5] text-ink-muted">
        Group any number of accounts that belong to the same person, including
        multiple accounts on one platform. Suggestions are based on Full Name
        matches, but no identity is linked until you review and confirm it.
        Conflicting links must be removed before accounts can be linked.
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
              Link or extend an identity group
            </h3>
            <div className="flex flex-wrap items-end gap-3">
              <SearchPicker
                label="First platform identity"
                value={firstIdentityId}
                options={identityOptions}
                onChange={setFirstIdentityId}
                placeholder="Select identity"
                searchPlaceholder="Search name, username, or ID"
                allLabel="Select identity"
                emptyMessage="No identities match these filters."
              />
              <SearchPicker
                label="Second platform identity"
                value={secondIdentityId}
                options={identityOptions}
                onChange={setSecondIdentityId}
                placeholder="Select identity"
                searchPlaceholder="Search name, username, or ID"
                allLabel="Select identity"
                emptyMessage="No identities match these filters."
              />
              <Button
                variant="positive"
                type="button"
                disabled={saving || !canLink}
                onClick={() => void performLink()}
              >
                Link identities
              </Button>
            </div>
            {!canLink && (
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
              <div
                aria-label="Current identity links"
                className="max-h-[600px] space-y-3 overflow-y-auto pr-2"
              >
                {linkedGroups.map(({ groupId, members }) => (
                  <div
                    className="rounded-lg border border-border-muted bg-surface p-4"
                    key={groupId}
                  >
                    <p className="mb-2 text-label font-semibold text-ink-muted">
                      Linked person group {groupId}
                    </p>
                    <ul className="flex flex-wrap items-center gap-3">
                      {members.map(({ identity, label, platformLabel }) => (
                        <li
                          className="flex flex-wrap items-center gap-2 rounded-md border border-border-muted px-3 py-2"
                          key={identity.identity_id}
                        >
                          <span className="text-small text-ink">
                            <strong>{platformLabel}</strong>:{" "}
                            {label}{" "}
                            <span className="font-mono text-caption text-ink-muted">
                              ({identity.platform_user_id})
                            </span>
                          </span>
                          <Button
                            variant="danger"
                            type="button"
                            disabled={saving}
                            onClick={() => void performUnlink(identity)}
                          >
                            Unlink {platformLabel}: {label}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="mb-7" aria-labelledby="suggested-links-title">
            <h3
              id="suggested-links-title"
              className="mb-3 text-subheading font-bold text-ink"
            >
              Suggested links
            </h3>
            {suggestedLinks.length === 0 ? (
              <p className="text-small text-ink-muted">
                No Full Name matches found among unlinked identities.
              </p>
            ) : (
              <ul
                aria-label="Suggested identity links"
                className="max-h-[600px] space-y-2 overflow-y-auto pr-2"
              >
                {suggestedLinks.map((suggestion) => (
                  <li
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border-muted bg-surface p-3"
                    key={`${suggestion.first.identity_id}-${suggestion.second.identity_id}`}
                  >
                    <span className="text-small text-ink">
                      <strong>{suggestion.reason}:</strong>{" "}
                      {suggestion.firstPlatformLabel}: {suggestion.firstLabel}{" "}
                      ({suggestion.first.platform_user_id}) ↔{" "}
                      {suggestion.secondPlatformLabel}: {suggestion.secondLabel}{" "}
                      ({suggestion.second.platform_user_id})
                    </span>
                    <Button
                      variant="positive"
                      type="button"
                      disabled={saving}
                      onClick={() =>
                        void performLink(
                          suggestion.first.identity_id,
                          suggestion.second.identity_id,
                        )
                      }
                    >
                      Link identities
                    </Button>
                  </li>
                ))}
              </ul>
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
