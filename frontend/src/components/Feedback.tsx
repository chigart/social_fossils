import type { PaginationMetadata } from "../api";
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

export function PaginationControls({
  pagination,
  onPageChange,
  label = "Pagination",
}: {
  pagination: PaginationMetadata;
  onPageChange: (page: number) => void;
  label?: string;
}) {
  const pageCount = Math.max(
    1,
    Math.ceil(pagination.total / pagination.page_size),
  );
  const currentPage = Math.min(Math.max(pagination.page, 1), pageCount);
  const pageNumbers = new Set<number>();
  if (pageCount <= 7) {
    for (let page = 1; page <= pageCount; page += 1) {
      pageNumbers.add(page);
    }
  } else {
    for (let page = 1; page <= 5; page += 1) {
      pageNumbers.add(page);
    }
    for (
      let page = Math.max(1, currentPage - 1);
      page <= Math.min(pageCount, currentPage + 1);
      page += 1
    ) {
      pageNumbers.add(page);
    }
    for (let page = pageCount - 2; page <= pageCount; page += 1) {
      pageNumbers.add(page);
    }
  }
  const pages = [...pageNumbers].sort((left, right) => left - right);
  const pageItems: (number | "ellipsis")[] = [];
  pages.forEach((page, index) => {
    if (index > 0 && page - pages[index - 1] > 2) {
      pageItems.push("ellipsis");
    } else if (index > 0 && page - pages[index - 1] === 2) {
      pageItems.push(page - 1);
    }
    pageItems.push(page);
  });

  return (
    <nav
      aria-label={label}
      className="mt-4 flex flex-wrap items-center justify-between gap-3 text-small text-ink-muted"
    >
      <span>
        Page {pagination.page} of {pageCount} · {pagination.total} items
      </span>
      <div className="flex flex-wrap items-center justify-end gap-2">
        <button
          className="rounded-md border border-border-input bg-surface px-3 py-2 disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(pagination.page - 1)}
        >
          Previous
        </button>
        {pageItems.map((item, index) =>
          item === "ellipsis" ? (
            <span
              key={`ellipsis-${index}`}
              className="px-1"
              aria-hidden="true"
            >
              …
            </span>
          ) : (
            <button
              key={item}
              className={`min-w-10 rounded-md border px-3 py-2 ${
                item === currentPage
                  ? "border-brand bg-brand text-white"
                  : "border-border-input bg-surface hover:bg-surface-subtle"
              }`}
              type="button"
              aria-label={`Go to page ${item}`}
              aria-current={item === currentPage ? "page" : undefined}
              onClick={() => onPageChange(item)}
            >
              {item}
            </button>
          ),
        )}
        <button
          className="rounded-md border border-border-input bg-surface px-3 py-2 disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          disabled={currentPage >= pageCount}
          onClick={() => onPageChange(pagination.page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
