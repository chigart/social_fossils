import { useState } from "react";
import type {
  IdentityLinksResponse,
  PlatformIdentity,
  UnidentifiedContact,
} from "../api";
import type { Resource } from "../types";

function identityLabel(identity: PlatformIdentity | undefined): string {
  if (!identity) return "Unknown identity";
  const contact = identity.contacts.find((item) => item.display_name) ??
    identity.contacts.find((item) => item.username);
  return contact?.display_name ??
    contact?.username ??
    `${identity.platform} ${identity.platform_user_id}`;
}

function contactLabel(contact: UnidentifiedContact): string {
  return contact.display_name || contact.username || "Unnamed contact";
}

export function useIdentityLinks(
  identityLinks: Resource<IdentityLinksResponse>,
  onLink: (firstIdentityId: number, secondIdentityId: number) => Promise<void>,
  onUnlink: (identityId: number) => Promise<void>,
) {
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

  const identityOptions = identities.map((identity) => ({
    identity,
    label: identityLabel(identity),
  }));
  const linkedGroups = [...groups.entries()].map(([groupId, members]) => ({
    groupId,
    members: members.map((identity) => ({
      identity,
      label: identityLabel(identity),
    })),
  }));
  const unidentifiedContacts = (identityLinks.data?.contacts_without_identity ?? [])
    .map((contact) => ({ contact, label: contactLabel(contact) }));
  const historyEvents = (identityLinks.data?.events ?? []).map((event) => {
    const identityName = identityLabel(identityById.get(event.identity_id));
    const peerName = event.peer_identity_id === null
      ? ""
      : ` and ${identityLabel(identityById.get(event.peer_identity_id))}`;
    return {
      id: event.id,
      description: `${event.action === "linked" ? "Linked" : "Unlinked"} ${identityName}${peerName} · ${event.source} · ${new Date(event.occurred_at).toLocaleString()}`,
    };
  });

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

  return {
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
  };
}
