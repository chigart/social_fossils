import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getUploadJobStatus,
  retryUploadJob,
  uploadFile,
  type UploadJob,
  type UploadJobStatus,
  type UploadProgress,
} from "../api";
import { UploadView } from "./UploadView";

vi.mock("../api", () => ({
  getUploadJobStatus: vi.fn(() => new Promise(() => {})),
  retryUploadJob: vi.fn(),
  uploadFile: vi.fn(),
}));

describe("UploadView", () => {
  beforeEach(() => {
    vi.mocked(getUploadJobStatus).mockImplementation(() => new Promise(() => {}));
  });

  it("requires an explicit platform before choosing an export", () => {
    render(<UploadView />);

    expect(screen.getByLabelText("Messaging platform")).toHaveValue("");
    expect(screen.getByLabelText("Choose export files")).toBeDisabled();
  });

  it("submits each selected file independently and shows its own outcome", async () => {
    const user = userEvent.setup();
    const uploadMock = vi.mocked(uploadFile);
    uploadMock.mockImplementation(async (file) => {
      if (file.name === "invalid.json") {
        throw new Error("Invalid Telegram export.");
      }

      return {
        id: 42,
        filename: file.name,
        platform: "telegram",
        status: "pending",
        source_account_id: null,
        import_session_id: null,
        airflow_dag_run_id: "run-42",
        started_at: null,
        finished_at: null,
        error_message: null,
        created_at: "2026-10-22T12:00:00Z",
      };
    });

    render(<UploadView />);
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "telegram",
    );
    const fileInput = screen.getByLabelText("Choose Telegram JSON files");
    const validFile = new File(["synthetic"], "valid.json", {
      type: "application/json",
    });
    const invalidFile = new File(["synthetic"], "invalid.json", {
      type: "application/json",
    });

    await user.upload(fileInput, [validFile, invalidFile]);
    expect(fileInput).toHaveAttribute("multiple");
    expect(screen.getByText("valid.json")).toBeInTheDocument();
    expect(screen.getByText("invalid.json")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Upload 2 files" }));

    const results = await screen.findByRole("list", {
      name: "Selected files and upload results",
    });
    expect(within(results).getByText(/Pipeline queued · Job #42 · pending/))
      .toBeInTheDocument();
    expect(within(results).getByRole("alert")).toHaveTextContent(
      "Invalid Telegram export.",
    );
    expect(uploadMock).toHaveBeenCalledTimes(2);
    expect(uploadMock).toHaveBeenNthCalledWith(
      1,
      validFile,
      "telegram",
      expect.any(Function),
    );
    expect(uploadMock).toHaveBeenNthCalledWith(
      2,
      invalidFile,
      "telegram",
      expect.any(Function),
    );
  });

  it("shows each file's transfer progress and handles an unknown total", async () => {
    const user = userEvent.setup();
    const job: UploadJob = {
      id: 45,
      filename: "progress.json",
      platform: "telegram",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "run-45",
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: "2026-10-22T12:00:00Z",
    };
    let resolveUpload: ((result: UploadJob) => void) | undefined;
    let reportProgress: ((progress: UploadProgress) => void) | undefined;
    const pendingUpload = new Promise<UploadJob>((resolve) => {
      resolveUpload = resolve;
    });
    vi.mocked(uploadFile).mockImplementation(
      (_file, _platform, onProgress) => {
        reportProgress = onProgress;
        return pendingUpload;
      },
    );

    render(<UploadView />);
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "telegram",
    );
    await user.upload(
      screen.getByLabelText("Choose Telegram JSON files"),
      new File(["synthetic"], "progress.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Upload 1 files" }));

    const progress = screen.getByRole("progressbar", {
      name: "Upload progress for progress.json",
    });
    act(() => reportProgress?.({ loadedBytes: 25, totalBytes: 100 }));
    expect(progress).toHaveValue(25);

    act(() => reportProgress?.({ loadedBytes: 50 }));
    expect(progress).not.toHaveAttribute("value");

    await act(async () => resolveUpload?.(job));
    expect(await screen.findByText(/Pipeline queued · Job #45/))
      .toBeInTheDocument();
  });

  it("polls Airflow task states until the job reaches a terminal state", async () => {
    vi.useFakeTimers();
    const job: UploadJob = {
      id: 46,
      filename: "tasked.json",
      platform: "telegram",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "run-46",
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: "2026-10-22T12:00:00Z",
    };
    const runningStatus: UploadJobStatus = {
      ...job,
      status: "processing",
      airflow_run_details: {
        state: "running",
        start_date: "2026-10-22T12:01:00Z",
        end_date: null,
      },
      airflow_tasks: [
        {
          task_id: "validate_export",
          state: "success",
          start_date: "2026-10-22T12:01:00Z",
          end_date: "2026-10-22T12:01:01Z",
        },
        {
          task_id: "perform_import",
          state: "running",
          start_date: "2026-10-22T12:01:01Z",
          end_date: null,
        },
      ],
    };
    const completedStatus: UploadJobStatus = {
      ...runningStatus,
      status: "completed",
      airflow_run_details: {
        state: "success",
        start_date: "2026-10-22T12:01:00Z",
        end_date: "2026-10-22T12:02:00Z",
      },
      airflow_tasks: runningStatus.airflow_tasks?.map((task) => ({
        ...task,
        state: "success",
      })),
    };
    vi.mocked(getUploadJobStatus).mockClear();
    vi.mocked(uploadFile).mockResolvedValue(job);
    vi.mocked(getUploadJobStatus)
      .mockResolvedValueOnce(runningStatus)
      .mockResolvedValueOnce(completedStatus);

    const { unmount } = render(<UploadView />);
    try {
      fireEvent.change(screen.getByLabelText("Messaging platform"), {
        target: { value: "telegram" },
      });
      fireEvent.change(screen.getByLabelText("Choose Telegram JSON files"), {
        target: {
          files: [new File(["synthetic"], "tasked.json", { type: "application/json" })],
        },
      });
      fireEvent.click(screen.getByRole("button", { name: "Upload 1 files" }));

      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(screen.getByText("Airflow run · running")).toBeInTheDocument();
      expect(getUploadJobStatus).toHaveBeenCalledTimes(1);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
      expect(screen.getByText("Airflow run · success")).toBeInTheDocument();
      expect(getUploadJobStatus).toHaveBeenCalledTimes(2);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
      expect(getUploadJobStatus).toHaveBeenCalledTimes(2);
    } finally {
      unmount();
      vi.useRealTimers();
    }
  });

  it("offers retry when a job was saved but its pipeline did not start", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadFile).mockResolvedValue({
      id: 73,
      filename: "waiting.json",
      platform: "telegram",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: null,
      started_at: null,
      finished_at: null,
      error_message: "Airflow is temporarily unavailable.",
      created_at: "2026-10-22T12:00:00Z",
    });
    vi.mocked(retryUploadJob).mockResolvedValue({
      id: 73,
      filename: "waiting.json",
      platform: "telegram",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "upload_job_73",
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: "2026-10-22T12:00:00Z",
    });

    render(<UploadView />);
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "telegram",
    );
    await user.upload(
      screen.getByLabelText("Choose Telegram JSON files"),
      new File(["synthetic"], "waiting.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Upload 1 files" }));

    expect(
      await screen.findByText(/pipeline did not start.*Airflow is temporarily unavailable/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry pipeline" }));

    expect(await screen.findByText(/Pipeline queued · Job #73/)).toBeInTheDocument();
    expect(retryUploadJob).toHaveBeenCalledWith(73);
  });

  it("uploads Instagram archives with the selected platform", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadFile).mockResolvedValue({
      id: 81,
      filename: "instagram.zip",
      platform: "instagram",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "run-81",
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: "2026-10-22T12:00:00Z",
    });

    render(<UploadView />);
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "instagram",
    );
    const fileInput = screen.getByLabelText("Choose Instagram ZIP files");
    const archive = new File(["synthetic"], "instagram.zip", {
      type: "application/zip",
    });
    await user.upload(fileInput, archive);
    expect(fileInput).toHaveAttribute("accept", ".zip,application/zip");
    await user.click(screen.getByRole("button", { name: "Upload 1 files" }));

    expect(await screen.findByText("instagram.zip")).toBeInTheDocument();
    expect(uploadFile).toHaveBeenCalledWith(
      archive,
      "instagram",
      expect.any(Function),
    );
  });

  it("uploads Facebook JSON archives with the selected platform", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadFile).mockResolvedValue({
      id: 83,
      filename: "facebook.zip",
      platform: "facebook",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "run-83",
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: "2026-10-22T12:00:00Z",
    });

    render(<UploadView />);
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "facebook",
    );
    const fileInput = screen.getByLabelText("Choose Facebook ZIP files");
    const archive = new File(["synthetic"], "facebook.zip", {
      type: "application/zip",
    });
    await user.upload(fileInput, archive);
    expect(fileInput).toHaveAttribute("accept", ".zip,application/zip");
    await user.click(screen.getByRole("button", { name: "Upload 1 files" }));

    expect(await screen.findByText("facebook.zip")).toBeInTheDocument();
    expect(uploadFile).toHaveBeenCalledWith(
      archive,
      "facebook",
      expect.any(Function),
    );
  });

  it("uploads VK archives with the selected platform", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadFile).mockResolvedValue({
      id: 84,
      filename: "vk.zip",
      platform: "vk",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "run-84",
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: "2026-10-22T12:00:00Z",
    });

    render(<UploadView />);
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "vk",
    );
    const fileInput = screen.getByLabelText("Choose VK ZIP files");
    const archive = new File(["synthetic"], "vk.zip", {
      type: "application/zip",
    });
    await user.upload(fileInput, archive);
    expect(fileInput).toHaveAttribute("accept", ".zip,application/zip");
    await user.click(screen.getByRole("button", { name: "Upload 1 files" }));

    expect(await screen.findByText("vk.zip")).toBeInTheDocument();
    expect(uploadFile).toHaveBeenCalledWith(
      archive,
      "vk",
      expect.any(Function),
    );
  });

  it("shows duplicate uploads as an informational warning and still queues them", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadFile).mockResolvedValue({
      id: 82,
      filename: "instagram.zip",
      platform: "instagram",
      status: "pending",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "run-82",
      started_at: null,
      finished_at: null,
      error_message: null,
      warning_message: "This file has already been uploaded",
      created_at: "2026-10-24T12:00:00Z",
    });

    render(<UploadView />);
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "instagram",
    );
    await user.upload(
      screen.getByLabelText("Choose Instagram ZIP files"),
      new File(["synthetic archive"], "instagram.zip", {
        type: "application/zip",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Upload 1 files" }));

    const warning = await screen.findByRole("status");
    expect(warning).toHaveTextContent("This file has already been uploaded");
    expect(warning).toHaveClass("text-ink-muted");
    expect(warning).not.toHaveClass("text-ink-warning");
    expect(
      screen.getByText(/Pipeline queued · Job #82/),
    ).toBeInTheDocument();
  });
});
