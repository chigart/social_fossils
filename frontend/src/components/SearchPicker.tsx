import { useMemo, useRef, useState } from "react";
import { SEARCH_PICKER_OPTION_LIMIT } from "../constants";
import { platformAccountPrefix } from "../utils/platforms";
import { PlatformAccountBadge } from "./PlatformAccountBadge";

export type SearchPickerOption = {
  value: string;
  label: string;
  platforms: string[];
  searchTerms?: string[];
};

function PickerOptionLabel({
  label,
  platforms,
}: {
  label: string;
  platforms: string[];
}) {
  if (platforms.length === 0) return <span>{label}</span>;

  return (
    <span className="flex flex-wrap gap-1">
      {platforms.map((platform) => (
        <PlatformAccountBadge
          key={platform}
          platform={platform}
          accountLabel={label}
          className="inline-block max-w-full whitespace-normal break-words rounded px-2 py-1 text-small font-normal"
        />
      ))}
    </span>
  );
}

export function SearchPicker({
  label,
  value,
  options,
  onChange,
  placeholder = "Select a name",
  searchPlaceholder = "Search name, platform, or ID",
  allLabel = "Show all",
  emptyMessage = "No names match these filters.",
}: {
  label: string;
  value: string;
  options: SearchPickerOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  allLabel?: string;
  emptyMessage?: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [platformFilter, setPlatformFilter] = useState("");
  const isInteractingWithOptions = useRef(false);
  const selected = options.find((option) => option.value === value);
  const platforms = [...new Set(options.flatMap((option) => option.platforms))]
    .sort();
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const matchingOptions = useMemo(
    () => options.filter((option) => {
      const matchesPlatform =
        platformFilter === "" || option.platforms.includes(platformFilter);
      const matchesSearch =
        normalizedSearch === "" ||
        [option.label, ...option.platforms, ...(option.searchTerms ?? [])].some(
          (candidate) =>
            candidate.toLocaleLowerCase().includes(normalizedSearch),
        );
      return matchesPlatform && matchesSearch;
    }),
    [options, platformFilter, normalizedSearch],
  );
  const visibleOptions = matchingOptions.slice(0, SEARCH_PICKER_OPTION_LIMIT);

  const close = () => {
    setOpen(false);
    setSearch("");
    setPlatformFilter("");
  };

  return (
    <div className="flex min-w-[220px] flex-1 flex-col gap-1 text-caption font-semibold text-ink-subtle">
      <span>{label}</span>
      <div
        className="relative"
        onBlur={(event) => {
          if (isInteractingWithOptions.current) return;
          if (
            !(event.relatedTarget instanceof Node) ||
            !event.currentTarget.contains(event.relatedTarget)
          ) {
            close();
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
            if (event.key === "Escape") close();
          }}
        >
          {selected ? (
            <PickerOptionLabel
              label={selected.label}
              platforms={selected.platforms}
            />
          ) : (
            placeholder
          )}
        </button>
        {open && (
          <div className="absolute z-10 mt-1 w-full rounded-md border border-border bg-surface p-2 shadow-lg">
            <input
              aria-label={`${label} search`}
              autoComplete="off"
              className="mb-2 w-full rounded-md border border-border bg-surface px-2 py-1.5 text-small font-normal text-ink"
              onChange={(event) => setSearch(event.target.value)}
              placeholder={searchPlaceholder}
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
                  {platformAccountPrefix(platform)}
                </option>
              ))}
            </select>
            <button
              className="mb-2 w-full rounded px-2 py-2 text-left text-small font-normal text-ink-muted hover:bg-surface-subtle focus-visible:outline-2 focus-visible:outline-focus"
              type="button"
              onClick={() => {
                onChange("");
                close();
              }}
            >
              {allLabel}
            </button>
            <ul
              aria-label={`${label} options`}
              className="max-h-48 overflow-y-auto"
              onMouseDownCapture={() => {
                isInteractingWithOptions.current = true;
                window.setTimeout(() => {
                  isInteractingWithOptions.current = false;
                }, 0);
              }}
              role="listbox"
            >
              {visibleOptions.map((option) => (
                <li key={option.value}>
                  <button
                    aria-selected={option.value === value}
                    className="w-full rounded px-2 py-2 text-left text-small font-normal text-ink hover:bg-surface-subtle focus-visible:outline-2 focus-visible:outline-focus"
                    role="option"
                    type="button"
                    onClick={() => {
                      onChange(option.value);
                      close();
                    }}
                  >
                    <PickerOptionLabel
                      label={option.label}
                      platforms={option.platforms}
                    />
                  </button>
                </li>
              ))}
              {visibleOptions.length === 0 && (
                <li className="px-2 py-2 text-small font-normal text-ink-muted">
                  {emptyMessage}
                </li>
              )}
            </ul>
            {matchingOptions.length > SEARCH_PICKER_OPTION_LIMIT && (
              <p className="m-0 px-2 py-2 text-caption font-normal text-ink-muted">
                Showing the first {SEARCH_PICKER_OPTION_LIMIT} matches. Refine
                your search to see other options.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
