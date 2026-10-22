import { useRef, useState } from "react";
import { uploadFile, type UploadJob } from "../api";
import {
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../styles";

type UploadItem = {
  id: number;
  file: File;
  status: "queued" | "uploading" | "accepted" | "failed";
  job?: UploadJob;
  error?: string;
};

function uploadError(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to upload this file.";
}

export function UploadView() {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const nextId = useRef(0);

  const addFiles = (files: File[]) => {
    setItems((current) => [
      ...current,
      ...files.map((file) => ({
        id: nextId.current++,
        file,
        status: "queued" as const,
      })),
    ]);
  };

  const submitFiles = async () => {
    const queuedItems = items.filter((item) => item.status === "queued");
    if (queuedItems.length === 0) return;

    setIsSubmitting(true);
    setItems((current) =>
      current.map((item) =>
        item.status === "queued" ? { ...item, status: "uploading" } : item,
      ),
    );

    await Promise.all(
      queuedItems.map(async (item) => {
        try {
          const job = await uploadFile(item.file);
          setItems((current) =>
            current.map((currentItem) =>
              currentItem.id === item.id
                ? { ...currentItem, status: "accepted", job }
                : currentItem,
            ),
          );
        } catch (error) {
          setItems((current) =>
            current.map((currentItem) =>
              currentItem.id === item.id
                ? {
                    ...currentItem,
                    status: "failed",
                    error: uploadError(error),
                  }
                : currentItem,
            ),
          );
        }
      }),
    );
    setIsSubmitting(false);
  };

  const queuedCount = items.filter((item) => item.status === "queued").length;

  return (
    <section
      id="uploads"
      className={sectionClassName}
      aria-labelledby="uploads-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>TELEGRAM EXPORTS</p>
          <h2 id="uploads-title" className={sectionTitleClassName}>
            Import files
          </h2>
        </div>
      </div>

      <p className="mb-4 text-small leading-[1.5] text-ink-muted">
        Select one or more Telegram JSON exports. Each file is uploaded and
        processed as its own pipeline, so a problem with one file will not stop
        the others.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <label className="inline-flex min-h-[40px] cursor-pointer items-center rounded-md border border-border-input bg-surface px-4 py-2 text-small font-semibold text-ink hover:bg-surface-muted focus-within:outline-3 focus-within:outline-focus focus-within:outline-offset-2">
          Choose files
          <input
            className="sr-only"
            type="file"
            accept=".json,application/json"
            multiple
            aria-label="Choose Telegram JSON files"
            disabled={isSubmitting}
            onChange={(event) => {
              addFiles(Array.from(event.currentTarget.files ?? []));
              event.currentTarget.value = "";
            }}
          />
        </label>
        <button
          className="min-h-[40px] cursor-pointer rounded-md border-0 bg-brand px-4 py-2 text-small font-semibold text-white hover:bg-brand-strong focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          disabled={queuedCount === 0 || isSubmitting}
          onClick={() => void submitFiles()}
        >
          {isSubmitting ? "Uploading…" : `Upload ${queuedCount} files`}
        </button>
      </div>

      {items.length === 0 ? (
        <p className="mt-4 text-small text-ink-muted">
          No files selected. Files are processed independently and are not
          displayed in analytics until their imports complete.
        </p>
      ) : (
        <ul
          className="mt-5 divide-y divide-border-subtle rounded-lg border border-border-subtle p-0"
          aria-label="Selected files and upload results"
        >
          {items.map((item) => (
            <li
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
            >
              <div className="min-w-0">
                <p className="m-0 break-all text-small font-semibold text-ink">
                  {item.file.name}
                </p>
                {item.status === "queued" && (
                  <p className="m-0 mt-1 text-caption text-ink-muted">
                    Ready to upload
                  </p>
                )}
                {item.status === "uploading" && (
                  <p className="m-0 mt-1 text-caption text-ink-muted" role="status">
                    Uploading…
                  </p>
                )}
                {item.status === "accepted" && item.job && (
                  <p className="m-0 mt-1 text-caption text-ink-green">
                    Upload accepted · Job #{item.job.id} · {item.job.status}
                  </p>
                )}
                {item.status === "failed" && (
                  <p className="m-0 mt-1 text-caption text-ink-warning" role="alert">
                    {item.error}
                  </p>
                )}
              </div>
              {item.status === "queued" && (
                <button
                  className="cursor-pointer rounded-md border border-border-input bg-surface px-3 py-1.5 text-caption font-semibold text-ink-subtle hover:bg-surface-muted focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-2"
                  type="button"
                  aria-label={`Remove ${item.file.name}`}
                  onClick={() =>
                    setItems((current) =>
                      current.filter((currentItem) => currentItem.id !== item.id),
                    )
                  }
                >
                  Remove
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
