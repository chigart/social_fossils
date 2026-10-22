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
    expect(uploadMock).toHaveBeenNthCalledWith(1, validFile);
    expect(uploadMock).toHaveBeenNthCalledWith(2, invalidFile);
  });

  it("offers retry when a job was saved but its pipeline did not start", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadFile).mockResolvedValue({
      id: 73,
      filename: "waiting.json",
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
});
