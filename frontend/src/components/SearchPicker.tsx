import { useRef, useState } from "react";
import { PLATFORM_ACCOUNT_PREFIXES } from "../platforms";

export type SearchPickerOption = {
  value: string;
  label: string;
  platforms: string[];
  searchTerms?: string[];
};

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
  const visibleOptions = options.filter((option) => {
    const matchesPlatform =
      platformFilter === "" || option.platforms.includes(platformFilter);
    const matchesSearch =
      normalizedSearch === "" ||
      [option.label, ...option.platforms, ...(option.searchTerms ?? [])].some(
        (candidate) =>
          candidate.toLocaleLowerCase().includes(normalizedSearch),
      );
    return matchesPlatform && matchesSearch;
  });

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
          {selected?.label ?? placeholder}
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
                  {PLATFORM_ACCOUNT_PREFIXES[platform.toLowerCase()] ??
                    platform.slice(0, 2).toUpperCase()}
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
                    <span className="block">{option.label}</span>
                    <span className="block text-caption text-ink-muted">
                      {option.platforms.map(
                        (platform) =>
                          PLATFORM_ACCOUNT_PREFIXES[platform.toLowerCase()] ??
                          platform.slice(0, 2).toUpperCase(),
                      ).join(", ")}
                    </span>
                  </button>
                </li>
              ))}
              {visibleOptions.length === 0 && (
                <li className="px-2 py-2 text-small font-normal text-ink-muted">
                  {emptyMessage}
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
