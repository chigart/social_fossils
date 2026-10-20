import type { SortDirection } from "../types";

export function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <article className="min-h-28 rounded-lg border border-border-subtle bg-surface-subtle p-4">
      <h3 className="mb-3 text-caption font-semibold text-ink-muted">{label}</h3>
      <p className="m-0 break-words text-metric font-bold tracking-[-0.04em] text-ink">
        {value}
      </p>
      {detail && <p className="mt-1 text-label text-ink-muted">{detail}</p>}
    </article>
  );
}

export function LoadingMessage() {
  return (
    <p className="m-0 py-[18px] text-ui text-ink-muted" role="status">
      <span
        className="mr-[9px] inline-block size-2 rounded-full bg-brand"
        aria-hidden="true"
      />
      Loading analytics…
    </p>
  );
}

export function SectionError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      className="flex items-center justify-between gap-[18px] rounded-lg border border-border-warning bg-surface-warning p-[15px] text-ui text-ink-warning max-sm:items-start"
      role="alert"
    >
      <p className="m-0">{message}</p>
      <button
        className="shrink-0 cursor-pointer rounded-md border border-border-warning-button bg-surface px-3 py-2 text-small font-semibold text-ink-warning-button hover:bg-surface-warning-hover focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-3"
        onClick={onRetry}
      >
        Retry
      </button>
    </div>
  );
}

export function SortButton({
  label,
  active,
  direction,
  onClick,
}: {
  label: string;
  active: boolean;
  direction: SortDirection;
  onClick: () => void;
}) {
  return (
    <button
      className="cursor-pointer border-0 bg-clear p-0 text-inherit hover:text-brand-strong focus-visible:rounded-sm focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-3"
      aria-label={`Sort by ${label}${active ? `, ${direction === "asc" ? "ascending" : "descending"}` : ""}`}
      aria-pressed={active}
      onClick={onClick}
    >
      {label}
      <span aria-hidden="true">
        {active ? (direction === "asc" ? " ↑" : " ↓") : ""}
      </span>
    </button>
  );
}
