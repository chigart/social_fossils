import { useRef, useState } from "react";
import {
  retryUploadJob,
  uploadFile,
  type UploadJob,
  type UploadPlatform,
} from "../api";

export type UploadItem = {
  id: number;
  file: File;
  platform: UploadPlatform;
  status: "queued" | "uploading" | "accepted" | "failed";
  job?: UploadJob;
  error?: string;
};

function uploadError(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to upload this file.";
}

export function useUploadQueue() {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const nextId = useRef(0);

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
        item.status === "queued" ? { ...item, status: "uploading" } : item,
      ),
    );

    await Promise.all(
      queuedItems.map(async (item) => {
        try {
          const job = await uploadFile(item.file, item.platform);
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

  const removeFile = (id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  };

  const retryPipeline = async (item: UploadItem) => {
    if (!item.job) return;
    setItems((current) =>
      current.map((currentItem) =>
        currentItem.id === item.id
          ? { ...currentItem, status: "uploading", error: undefined }
          : currentItem,
      ),
    );

    try {
      const job = await retryUploadJob(item.job.id);
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
