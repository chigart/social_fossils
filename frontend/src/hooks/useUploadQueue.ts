import { useEffect, useRef, useState } from "react";
import {
  getUploadJobStatus,
  retryUploadJob,
  uploadFile,
  type UploadJob,
  type UploadJobStatus,
  type UploadPlatform,
  type UploadProgress,
} from "../api";

export type UploadItem = {
  id: number;
  file: File;
  platform: UploadPlatform;
  status: "queued" | "uploading" | "accepted" | "failed";
  progress?: number | null;
  job?: UploadJob;
  airflowStatus?: UploadJobStatus;
  airflowRefreshError?: string;
  error?: string;
};

const airflowPollIntervalMs = 3000;

function uploadError(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to upload this file.";
}

export function useUploadQueue() {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const nextId = useRef(0);

  const activeJobs = items
    .flatMap((item) => {
      const job = item.job;
      return job?.airflow_dag_run_id &&
        job.status !== "completed" &&
        job.status !== "failed"
        ? [{ itemId: item.id, jobId: job.id }]
        : [];
    });
  const activeJobKey = activeJobs
    .map(({ itemId, jobId }) => `${itemId}:${jobId}`)
    .join(",");

  useEffect(() => {
    if (activeJobs.length === 0) return;

    let cancelled = false;
    let timeout: ReturnType<typeof setTimeout> | undefined;

    const refreshStatuses = async () => {
      await Promise.all(
        activeJobs.map(async ({ itemId, jobId }) => {
          try {
            const airflowStatus = await getUploadJobStatus(jobId);
            if (cancelled) return;

            setItems((current) =>
              current.map((item) => {
                if (item.id !== itemId || item.job?.id !== jobId) return item;
                return {
                  ...item,
                  job: airflowStatus,
                  airflowStatus: {
                    ...airflowStatus,
                    airflow_tasks:
                      airflowStatus.airflow_tasks ??
                      item.airflowStatus?.airflow_tasks,
                    airflow_run_details:
                      airflowStatus.airflow_run_details ??
                      item.airflowStatus?.airflow_run_details,
                  },
                  airflowRefreshError: airflowStatus.airflow_error,
                };
              }),
            );
          } catch (error) {
            if (cancelled) return;
            setItems((current) =>
              current.map((item) =>
                item.id === itemId && item.job?.id === jobId
                  ? { ...item, airflowRefreshError: uploadError(error) }
                  : item,
              ),
            );
          }
        }),
      );

      if (!cancelled) {
        timeout = setTimeout(refreshStatuses, airflowPollIntervalMs);
      }
    };

    void refreshStatuses();
    return () => {
      cancelled = true;
      if (timeout !== undefined) clearTimeout(timeout);
    };
  }, [activeJobKey]);

  const addFiles = (files: File[], platform: UploadPlatform) => {
    setItems((current) => [
      ...current,
      ...files.map((file) => ({
        id: nextId.current++,
        file,
        platform,
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
        item.status === "queued"
          ? { ...item, status: "uploading", progress: null }
          : item,
      ),
    );

    await Promise.all(
      queuedItems.map(async (item) => {
        try {
          const job = await uploadFile(
            item.file,
            item.platform,
            (progress: UploadProgress) => {
              const percent =
                progress.totalBytes !== undefined && progress.totalBytes > 0
                  ? Math.min(
                      100,
                      Math.max(
                        0,
                        Math.floor(
                          (progress.loadedBytes / progress.totalBytes) * 100,
                        ),
                      ),
                    )
                  : null;
              setItems((current) =>
                current.map((currentItem) =>
                  currentItem.id === item.id
                    ? { ...currentItem, progress: percent }
                    : currentItem,
                ),
              );
            },
          );
          setItems((current) =>
            current.map((currentItem) =>
              currentItem.id === item.id
                ? {
                    ...currentItem,
                    status: "accepted",
                    progress: undefined,
                    job,
                    airflowStatus: undefined,
                    airflowRefreshError: undefined,
                  }
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
                    progress: undefined,
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

  const removeFile = (id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  };

  const retryPipeline = async (item: UploadItem) => {
    if (!item.job) return;
    setItems((current) =>
      current.map((currentItem) =>
        currentItem.id === item.id
          ? {
              ...currentItem,
              status: "uploading",
              error: undefined,
              airflowRefreshError: undefined,
            }
          : currentItem,
      ),
    );

    try {
      const job = await retryUploadJob(item.job.id);
      setItems((current) =>
        current.map((currentItem) =>
          currentItem.id === item.id
            ? {
                ...currentItem,
                status: "accepted",
                job,
                airflowStatus: undefined,
                airflowRefreshError: undefined,
              }
            : currentItem,
        ),
      );
    } catch (error) {
      setItems((current) =>
        current.map((currentItem) =>
          currentItem.id === item.id
            ? {
                ...currentItem,
                status: "accepted",
                error: uploadError(error),
              }
            : currentItem,
        ),
      );
    }
  };

  const queuedCount = items.filter((item) => item.status === "queued").length;

  return {
    items,
    isSubmitting,
    queuedCount,
    addFiles,
    submitFiles,
    removeFile,
    retryPipeline,
  };
}
