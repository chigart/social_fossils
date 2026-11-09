import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { retryUploadJob, uploadFile } from "../api";
import { UploadView } from "./UploadView";

vi.mock("../api", () => ({
  retryUploadJob: vi.fn(),
  uploadFile: vi.fn(),
}));

describe("UploadView", () => {
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
    expect(uploadMock).toHaveBeenNthCalledWith(1, validFile, "telegram");
    expect(uploadMock).toHaveBeenNthCalledWith(2, invalidFile, "telegram");
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
    expect(uploadFile).toHaveBeenCalledWith(archive, "instagram");
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
    expect(uploadFile).toHaveBeenCalledWith(archive, "facebook");
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
