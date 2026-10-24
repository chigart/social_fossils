import { useState } from "react";
import type { PlatformIdentity } from "../api";
import { PLATFORM_ACCOUNT_PREFIXES } from "../platforms";

export type IdentityPickerOption = {
  identity: PlatformIdentity;
  label: string;
};

export function IdentityPicker({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: IdentityPickerOption[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [platformFilter, setPlatformFilter] = useState("");
  const selected = options.find(({ identity }) =>
    String(identity.identity_id) === value
  );
  const platforms = [...new Set(
    options.map(({ identity }) => identity.platform),
  )].sort();
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const visibleOptions = options.filter(({ identity, label: identityName }) => {
    const matchesPlatform =
      platformFilter === "" || identity.platform === platformFilter;
    const matchesSearch =
      normalizedSearch === "" ||
      [
        identityName,
        identity.platform_user_id,
        identity.platform,
        ...identity.contacts.map((contact) => contact.username ?? ""),
      ].some((candidate) =>
        candidate.toLocaleLowerCase().includes(normalizedSearch)
      );
    return matchesPlatform && matchesSearch;
  });

  return (
    <div className="flex min-w-[220px] flex-1 flex-col gap-1 text-caption font-semibold text-ink-subtle">
      <span>{label}</span>
      <div
        className="relative"
        onBlur={(event) => {
          if (
            !(event.relatedTarget instanceof Node) ||
            !event.currentTarget.contains(event.relatedTarget)
          ) {
            setOpen(false);
          }
        }}
      >
        <button
          aria-label={label}
          aria-expanded={open}
          aria-haspopup="listbox"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-left text-small font-normal text-ink"
          type="button"
          onClick={() => setOpen((isOpen) => !isOpen)}
          onKeyDown={(event) => {
            if (event.key === "Escape") setOpen(false);
          }}
        >
          {selected
            ? `${PLATFORM_ACCOUNT_PREFIXES[selected.identity.platform.toLowerCase()] ?? selected.identity.platform.slice(0, 2).toUpperCase()}: ${selected.label} (${selected.identity.platform_user_id})`
            : "Select identity"}
        </button>
        {open && (
          <div className="absolute z-10 mt-1 w-full rounded-md border border-border bg-surface p-2 shadow-lg">
            <input
              aria-label={`${label} search`}
              autoComplete="off"
              className="mb-2 w-full rounded-md border border-border bg-surface px-2 py-1.5 text-small font-normal text-ink"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name, username, or ID"
              type="search"
              value={search}
            />
            <select
              aria-label={`${label} platform filter`}
              className="mb-2 w-full rounded-md border border-border bg-surface px-2 py-1.5 text-small font-normal text-ink"
              onChange={(event) => setPlatformFilter(event.target.value)}
              value={platformFilter}
            >
              <option value="">All platforms</option>
              {platforms.map((platform) => (
                <option key={platform} value={platform}>
                  {PLATFORM_ACCOUNT_PREFIXES[platform.toLowerCase()] ??
                    platform.slice(0, 2).toUpperCase()}
                </option>
              ))}
            </select>
            <ul
              aria-label={`${label} options`}
              className="max-h-48 overflow-y-auto"
              role="listbox"
            >
              {visibleOptions.map(({ identity, label: identityName }) => (
                <li key={identity.identity_id}>
                  <button
                    aria-selected={String(identity.identity_id) === value}
                    className="w-full rounded px-2 py-2 text-left text-small font-normal text-ink hover:bg-surface-subtle focus-visible:outline-2 focus-visible:outline-focus"
                    role="option"
                    type="button"
                    onClick={() => {
                      onChange(String(identity.identity_id));
                      setOpen(false);
                    }}
                  >
                    {PLATFORM_ACCOUNT_PREFIXES[identity.platform.toLowerCase()] ??
                      identity.platform.slice(0, 2).toUpperCase()}: {identityName} (
                    {identity.platform_user_id})
                  </button>
                </li>
              ))}
              {visibleOptions.length === 0 && (
                <li className="px-2 py-2 text-small font-normal text-ink-muted">
                  No identities match these filters.
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
