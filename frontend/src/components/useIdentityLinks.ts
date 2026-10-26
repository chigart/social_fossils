import { useState } from "react";
import type {
  IdentityLinksResponse,
  PlatformIdentity,
} from "../api";
import { PLATFORM_ACCOUNT_PREFIXES } from "../platforms";
import type { Resource } from "../types";
import type { SearchPickerOption } from "./SearchPicker";

function identityLabel(identity: PlatformIdentity | undefined): string {
  if (!identity) return "Unknown identity";
  const contact = identity.contacts.find((item) => item.display_name) ??
    identity.contacts.find((item) => item.username);
  return contact?.display_name ??
    contact?.username ??
    identity.platform_user_id;
}

function identityFullName(identity: PlatformIdentity): string | null {
  return identity.contacts.find((contact) => contact.display_name?.trim())
    ?.display_name?.trim() ?? null;
}

function normalizedName(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function editDistanceWithinLimit(first: string, second: string, limit: number): number | null {
  const firstSymbols = Array.from(first);
  const secondSymbols = Array.from(second);
  if (Math.abs(firstSymbols.length - secondSymbols.length) > limit) return null;

  let previous = Array.from(
    { length: secondSymbols.length + 1 },
    (_, index) => index,
  );
  for (let row = 1; row <= firstSymbols.length; row += 1) {
    const current = [row];
    let rowMinimum = row;
    for (let column = 1; column <= secondSymbols.length; column += 1) {
      const cost = firstSymbols[row - 1] === secondSymbols[column - 1] ? 0 : 1;
      const distance = Math.min(
        previous[column] + 1,
        current[column - 1] + 1,
        previous[column - 1] + cost,
      );
      current.push(distance);
      rowMinimum = Math.min(rowMinimum, distance);
    }
    if (rowMinimum > limit) return null;
    previous = current;
  }
  return previous[secondSymbols.length] <= limit
    ? previous[secondSymbols.length]
    : null;
}

function hasMatchingFirstOrLastName(first: string, second: string): boolean {
  const firstParts = first.split(" ");
  const secondParts = second.split(" ");
  if (firstParts.length < 2 || secondParts.length < 2) return false;
  const firstNames = [firstParts[0], firstParts[firstParts.length - 1]];
  const secondNames = [secondParts[0], secondParts[secondParts.length - 1]];
  return firstNames.some((part) => secondNames.includes(part));
}

function suggestionRank(
  firstName: string,
  secondName: string,
): { rank: number; reason: string } | null {
  const first = normalizedName(firstName);
  const second = normalizedName(secondName);
  if (!first || !second) return null;
  if (first === second) return { rank: 0, reason: "Full Name match" };
  const distance = editDistanceWithinLimit(first, second, 2);
  if (distance === 1) return { rank: 1, reason: "1-symbol Full Name difference" };
  if (distance === 2) return { rank: 2, reason: "2-symbol Full Name difference" };
  if (hasMatchingFirstOrLastName(first, second)) {
    return { rank: 3, reason: "First or last name match" };
  }
  return null;
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
    value: String(identity.identity_id),
    label: `${
      PLATFORM_ACCOUNT_PREFIXES[identity.platform.toLowerCase()] ??
      identity.platform.slice(0, 2).toUpperCase()
    }: ${identityLabel(identity)} (${identity.platform_user_id})`,
    platforms: [identity.platform],
    searchTerms: [
      identity.platform_user_id,
      ...identity.contacts.map((contact) => contact.username ?? ""),
    ],
  })) satisfies SearchPickerOption[];
  const suggestedLinks = identities.flatMap((identity, index) => {
    const fullName = identityFullName(identity);
    if (!fullName || identity.identity_group_id !== null) return [];
    return identities.slice(index + 1).flatMap((candidate) => {
      const candidateName = identityFullName(candidate);
      if (
        !candidateName ||
        candidate.identity_group_id !== null ||
        candidate.platform === identity.platform
      ) {
        return [];
      }
      const match = suggestionRank(fullName, candidateName);
      return match
        ? [{
            first: identity,
            firstLabel: fullName,
            firstPlatformLabel:
              PLATFORM_ACCOUNT_PREFIXES[identity.platform.toLowerCase()] ??
              identity.platform.slice(0, 2).toUpperCase(),
            second: candidate,
            secondLabel: candidateName,
            secondPlatformLabel:
              PLATFORM_ACCOUNT_PREFIXES[candidate.platform.toLowerCase()] ??
              candidate.platform.slice(0, 2).toUpperCase(),
            reason: match.reason,
            rank: match.rank,
            sortLength: Math.max(
              Array.from(fullName).length,
              Array.from(candidateName).length,
            ),
            sortName: `${normalizedName(fullName)} ${normalizedName(candidateName)}`,
          }]
        : [];
    });
  }).sort((first, second) =>
    first.rank - second.rank ||
    second.sortLength - first.sortLength ||
    first.sortName.localeCompare(second.sortName) ||
    first.first.identity_id - second.first.identity_id ||
    first.second.identity_id - second.second.identity_id,
  );
  const linkedGroups = [...groups.entries()].map(([groupId, members]) => ({
    groupId,
    members: members.map((identity) => ({
      identity,
      label: identityLabel(identity),
      platformLabel:
        PLATFORM_ACCOUNT_PREFIXES[identity.platform.toLowerCase()] ??
        identity.platform.slice(0, 2).toUpperCase(),
    })),
  }));
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

  const performLink = async (
    firstIdentity = Number(firstIdentityId),
    secondIdentity = Number(secondIdentityId),
  ) => {
    const first = firstIdentity;
    const second = secondIdentity;
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
    canLink: identities.length >= 2,
    suggestedLinks,
    linkedGroups,
    historyEvents,
    performLink,
    performUnlink,
  };
}
