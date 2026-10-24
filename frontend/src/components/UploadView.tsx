import { useState } from "react";
import { PLATFORM_CONFIG, type UploadPlatform } from "../platforms";
import { useUploadQueue } from "../hooks/useUploadQueue";
import {
  sectionClassName,
  sectionEyebrowClassName,
  sectionHeaderClassName,
  sectionTitleClassName,
} from "../styles";

const isUploadPlatform = (value: string): value is UploadPlatform =>
  Object.prototype.hasOwnProperty.call(PLATFORM_CONFIG, value);

export function UploadView() {
  const [platform, setPlatform] = useState<UploadPlatform | "">("");
  const {
    items,
    isSubmitting,
    queuedCount,
    addFiles,
    submitFiles,
    removeFile,
    retryPipeline,
  } = useUploadQueue();
  const platformConfig = platform ? PLATFORM_CONFIG[platform] : undefined;

  return (
    <section
      id="uploads"
      className={sectionClassName}
      aria-labelledby="uploads-title"
    >
      <div className={sectionHeaderClassName}>
        <div>
          <p className={sectionEyebrowClassName}>
            {platformConfig
              ? `${platformConfig.label.toUpperCase()} EXPORTS`
              : "EXPORTS"}
          </p>
          <h2 id="uploads-title" className={sectionTitleClassName}>
            Import files
          </h2>
        </div>
      </div>

      <p className="mb-4 text-small leading-[1.5] text-ink-muted">
        {platformConfig?.instructions ??
          "Select a messaging platform to choose an export file."}{" "}
        Each file is uploaded and processed as its own pipeline, so a problem
        with one file will not stop the others.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex min-h-[40px] items-center gap-2 text-small font-semibold text-ink">
          Messaging platform
          <select
            className="min-h-[40px] rounded-md border border-border-input bg-surface px-3 py-2"
            aria-label="Messaging platform"
            value={platform}
            disabled={isSubmitting}
            onChange={(event) => {
              const value = event.currentTarget.value;
              if (isUploadPlatform(value)) {
                setPlatform(value);
              }
            }}
          >
            <option value="">Select a platform</option>
            {Object.entries(PLATFORM_CONFIG).map(([value, config]) => (
              <option key={value} value={value}>
                {config.label}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-flex min-h-[40px] cursor-pointer items-center rounded-md border border-border-input bg-surface px-4 py-2 text-small font-semibold text-ink hover:bg-surface-muted focus-within:outline-3 focus-within:outline-focus focus-within:outline-offset-2">
          Choose files
          <input
            className="sr-only"
            type="file"
            accept={platformConfig?.acceptedFileType ?? ""}
            multiple
            aria-label={
              platformConfig?.fileInputLabel ?? "Choose export files"
            }
            disabled={isSubmitting || !platform}
            onChange={(event) => {
              if (platform) {
                addFiles(Array.from(event.currentTarget.files ?? []), platform);
              }
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
                  item.job.airflow_dag_run_id ? (
                    <p className="m-0 mt-1 text-caption text-ink-green">
                      Pipeline queued · Job #{item.job.id} · {item.job.status}
                    </p>
                  ) : (
                    <p
                      className="m-0 mt-1 text-caption text-ink-warning"
                      role="alert"
                    >
                      Upload saved as job #{item.job.id}, but the pipeline did
                      not start. {item.error || item.job.error_message}
                    </p>
                  )
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
                  onClick={() => removeFile(item.id)}
                >
                  Remove
                </button>
              )}
              {item.status === "accepted" &&
                item.job &&
                !item.job.airflow_dag_run_id && (
                  <button
                    className="cursor-pointer rounded-md border border-border-warning-button bg-surface px-3 py-1.5 text-caption font-semibold text-ink-warning-button hover:bg-surface-warning-hover focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-2"
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => void retryPipeline(item)}
                  >
                    Retry pipeline
                  </button>
                )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
