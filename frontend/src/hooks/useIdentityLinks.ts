import { useEffect, useMemo, useState } from "react";
import type {
  IdentityLinksResponse,
  PaginationMetadata,
  PlatformIdentity,
} from "../api";
import { CYRILLIC_TO_LATIN, DEFAULT_PAGE_SIZE } from "../constants";
import { formatDate } from "../utils/format";
import { platformAccountPrefix } from "../utils/platforms";
import type { Resource } from "../types";
import type { SearchPickerOption } from "../components/SearchPicker";

function paginate<T>(items: T[], page: number) {
  const start = (page - 1) * DEFAULT_PAGE_SIZE;
  return {
    items: items.slice(start, start + DEFAULT_PAGE_SIZE),
    pagination: {
      page,
      page_size: DEFAULT_PAGE_SIZE,
      total: items.length,
    } satisfies PaginationMetadata,
  };
}

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

function suggestionName(fullName: string): string {
  return fullName.split("|", 1)[0].trim();
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

function transliteratedName(name: string): string {
  return normalizedName(
    Array.from(name.toLocaleLowerCase())
      .map((symbol) => CYRILLIC_TO_LATIN[symbol] ?? symbol)
      .join(""),
  );
}

function editDistanceWithinLimit(first: string, second: string): number | null {
  const firstSymbols = Array.from(first);
  const secondSymbols = Array.from(second);
  if (first === second) return 0;
  if (Math.abs(firstSymbols.length - secondSymbols.length) > 1) return null;

  let firstIndex = 0;
  let secondIndex = 0;
  let differences = 0;
  while (
    firstIndex < firstSymbols.length &&
    secondIndex < secondSymbols.length
  ) {
    if (firstSymbols[firstIndex] === secondSymbols[secondIndex]) {
      firstIndex += 1;
      secondIndex += 1;
      continue;
    }

    differences += 1;
    if (differences > 1) return null;
    if (firstSymbols.length > secondSymbols.length) firstIndex += 1;
    else if (secondSymbols.length > firstSymbols.length) secondIndex += 1;
    else {
      firstIndex += 1;
      secondIndex += 1;
    }
  }
  if (firstIndex < firstSymbols.length || secondIndex < secondSymbols.length) {
    differences += 1;
  }
  return differences === 1 ? 1 : null;
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
  const [linkedPage, setLinkedPage] = useState(1);
  const [suggestedPage, setSuggestedPage] = useState(1);
  const [historyPage, setHistoryPage] = useState(1);
  const identities = identityLinks.data?.identities ?? [];
  useEffect(() => {
    setLinkedPage(1);
    setSuggestedPage(1);
    setHistoryPage(1);
  }, [identityLinks.data]);
  const identityById = useMemo(
    () => new Map(identities.map((identity) => [identity.identity_id, identity])),
    [identities],
  );
  const identityOptions = useMemo(
    () => identities
      .filter((identity) => !identity.is_owner)
      .map((identity) => ({
        value: String(identity.identity_id),
        label: `${identityLabel(identity)} (${identity.platform_user_id})`,
        platforms: [identity.platform],
        searchTerms: [
          identity.platform_user_id,
          ...identity.contacts.map((contact) => contact.username ?? ""),
        ],
      })) satisfies SearchPickerOption[],
    [identities],
  );
  const linkedGroups = useMemo(() => {
    const groups = new Map<number, PlatformIdentity[]>();
    for (const identity of identities) {
      if (identity.identity_group_id === null) continue;
      const group = groups.get(identity.identity_group_id) ?? [];
      group.push(identity);
      groups.set(identity.identity_group_id, group);
    }
    const compareNames = (first: string, second: string) =>
      first.localeCompare(second, undefined, { sensitivity: "base", numeric: true });
    return [...groups.entries()].map(([groupId, groupMembers]) => {
      const members = [...groupMembers].sort((first, second) =>
        Number(identityFullName(first) === null) -
          Number(identityFullName(second) === null) ||
        compareNames(
          identityFullName(first) ?? identityLabel(first),
          identityFullName(second) ?? identityLabel(second),
        ) ||
        first.identity_id - second.identity_id,
      );
      const fullNames = members
        .map(identityFullName)
        .filter((name): name is string => name !== null);
      return {
        groupId,
        sortName: fullNames.sort(compareNames)[0] ??
          members.map(identityLabel).sort(compareNames)[0] ?? "",
        members: members.map((identity) => ({
          identity,
          label: identityLabel(identity),
          platformLabel: platformAccountPrefix(identity.platform),
        })),
      };
    }).sort((first, second) =>
      compareNames(first.sortName, second.sortName) ||
      first.groupId - second.groupId,
    );
  }, [identities]);
  const suggestedLinks = useMemo(() => {
    const identitiesByName = new Map<
      string,
      {
        identity: PlatformIdentity;
        label: string;
        name: string;
      }[]
    >();
    for (const identity of identities) {
      if (identity.is_owner) continue;
      const label = identityFullName(identity);
      if (!label) continue;
      const name = normalizedName(suggestionName(label));
      if (!name) continue;
      const aliases = [
        ...new Set([name, transliteratedName(suggestionName(label))]),
      ]
        .filter(Boolean);
      const namedIdentity = { identity, label, name };
      for (const alias of aliases) {
        const matches = identitiesByName.get(alias) ?? [];
        matches.push(namedIdentity);
        identitiesByName.set(alias, matches);
      }
    }

    const namesBySignature = new Map<string, Set<string>>();
    for (const name of identitiesByName.keys()) {
      const signatures = new Set([name]);
      const symbols = Array.from(name);
      for (let index = 0; index < symbols.length; index += 1) {
        signatures.add(
          symbols.slice(0, index).join("") + symbols.slice(index + 1).join(""),
        );
      }
      for (const signature of signatures) {
        const names = namesBySignature.get(signature) ?? new Set<string>();
        names.add(name);
        namesBySignature.set(signature, names);
      }
    }

    const candidateNamePairs = new Set(
      [...identitiesByName.keys()].map((name) => `${name}\u0000${name}`),
    );
    for (const names of namesBySignature.values()) {
      const candidates = [...names];
      for (let firstIndex = 0; firstIndex < candidates.length; firstIndex += 1) {
        for (
          let secondIndex = firstIndex + 1;
          secondIndex < candidates.length;
          secondIndex += 1
        ) {
          candidateNamePairs.add(
            `${candidates[firstIndex]}\u0000${candidates[secondIndex]}`,
          );
        }
      }
    }

    const suggestionsByIdentityPair = new Map<string, {
      first: PlatformIdentity;
      firstLabel: string;
      second: PlatformIdentity;
      secondLabel: string;
      reason: string;
      rank: number;
      sortLength: number;
      sortName: string;
    }>();
    for (const pair of candidateNamePairs) {
      const [firstName, secondName] = pair.split("\u0000");
      const distance = editDistanceWithinLimit(firstName, secondName);
      if (distance === null) continue;
      const firstIdentities = identitiesByName.get(firstName) ?? [];
      const secondIdentities = identitiesByName.get(secondName) ?? [];
      for (let firstIndex = 0; firstIndex < firstIdentities.length; firstIndex += 1) {
        const first = firstIdentities[firstIndex];
        const secondStart = firstName === secondName ? firstIndex + 1 : 0;
        for (const second of secondIdentities.slice(secondStart)) {
          if (first.identity.identity_id === second.identity.identity_id) continue;
          if (first.identity.platform === second.identity.platform) continue;
          if (
            first.identity.identity_group_id !== null &&
            first.identity.identity_group_id === second.identity.identity_group_id
          ) continue;

          const usesTransliteration =
            firstName !== first.name || secondName !== second.name;
          const reason = usesTransliteration
            ? distance === 0
              ? "Transliterated Full Name match"
              : "1-symbol transliterated Full Name difference"
            : distance === 0
              ? "Full Name match"
              : "1-symbol Full Name difference";
          const suggestion = {
            first: first.identity,
            firstLabel: first.label,
            second: second.identity,
            secondLabel: second.label,
            reason,
            rank: distance,
            sortLength: Math.max(
              Array.from(first.label).length,
              Array.from(second.label).length,
            ),
            sortName: [first.name, second.name].sort().join(" "),
          };
          const key = [
            first.identity.identity_id,
            second.identity.identity_id,
          ].sort((a, b) => a - b).join(":");
          const existing = suggestionsByIdentityPair.get(key);
          if (
            !existing ||
            suggestion.rank < existing.rank ||
            (suggestion.rank === existing.rank &&
              existing.reason.startsWith("Transliterated") &&
              !reason.startsWith("Transliterated"))
          ) {
            suggestionsByIdentityPair.set(key, suggestion);
          }
        }
      }
    }

    return [...suggestionsByIdentityPair.values()].sort((first, second) =>
      first.rank - second.rank ||
      second.sortLength - first.sortLength ||
      first.sortName.localeCompare(second.sortName) ||
      first.first.identity_id - second.first.identity_id ||
      first.second.identity_id - second.second.identity_id,
    );
  }, [identities]);
  const historyEvents = useMemo(
    () => (identityLinks.data?.events ?? []).map((event) => {
      const identityName = identityLabel(identityById.get(event.identity_id));
      const peerName = event.peer_identity_id === null
        ? ""
        : ` and ${identityLabel(identityById.get(event.peer_identity_id))}`;
      return {
        id: event.id,
        description: `${event.action === "linked" ? "Linked" : "Unlinked"} ${identityName}${peerName} · ${event.source} · ${formatDate(event.occurred_at)}`,
      };
    }),
    [identityLinks.data?.events, identityById],
  );
  const linkedGroupsPage = paginate(linkedGroups, linkedPage);
  const suggestedLinksPage = paginate(suggestedLinks, suggestedPage);
  const historyEventsPage = paginate(historyEvents, historyPage);

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
    canLink: identityOptions.length >= 2,
    suggestedLinks,
    linkedGroups,
    historyEvents,
    linkedGroupsPage,
    setLinkedPage,
    suggestedLinksPage,
    setSuggestedPage,
    historyEventsPage,
    setHistoryPage,
    performLink,
    performUnlink,
  };
}
