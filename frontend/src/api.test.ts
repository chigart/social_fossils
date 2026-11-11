import { describe, expect, it, vi } from "vitest";
import {
  getChats,
  getChatInsights,
  getCommunicationBalance,
  getCommunicationTimeline,
  getContacts,
  getForgottenContacts,
  getIdentityLinks,
  getOverview,
  getUploadJobStatus,
  linkPlatformIdentities,
  retryUploadJob,
  unlinkPlatformIdentity,
  uploadFile,
} from "./api";

class MockUploadRequest {
  upload: {
    onprogress: ((event: ProgressEvent) => void) | null;
  } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  status = 200;
  responseText = "";
  open = vi.fn();
  send = vi.fn((_body: FormData) => this.onload?.());
}

function mockUploadRequest(body: unknown, status = 200) {
  const request = new MockUploadRequest();
  request.status = status;
  request.responseText = JSON.stringify(body);
  vi.stubGlobal(
    "XMLHttpRequest",
    vi.fn(function MockXMLHttpRequest() {
      return request;
    }),
  );
  return request;
}

describe("analytics API helpers", () => {
  it("requests each analytics endpoint and returns its JSON data", async () => {
    const overview = { total_messages: 17 };
    const chats = [{ chat_id: 1 }];
    const chatInsights = { chats: [{ chat_id: 1 }] };
    const contacts = [{ account_id: 2 }];
    const balance = { summary: { eligible_contacts: 1 }, contacts: [] };
    const forgotten = { summary: { eligible_contacts: 1 }, contacts: [] };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => overview,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => chatInsights,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => chats,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => contacts,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => balance,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => forgotten,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ summary: {}, months: [] }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getOverview()).resolves.toEqual(overview);
    await expect(getChatInsights()).resolves.toEqual(chatInsights);
    await expect(getChats()).resolves.toEqual(chats);
    await expect(getContacts()).resolves.toEqual(contacts);
    await expect(getCommunicationBalance()).resolves.toEqual(balance);
    await expect(getForgottenContacts()).resolves.toEqual(forgotten);
    await expect(getCommunicationTimeline()).resolves.toEqual({
      summary: {},
      months: [],
    });

    expect(fetchMock.mock.calls).toEqual([
      ["/api/analytics/overview"],
      ["/api/analytics/chat-insights"],
      ["/api/analytics/chats"],
      ["/api/analytics/contacts"],
      ["/api/analytics/communication-balance"],
      ["/api/analytics/forgotten-contacts"],
      ["/api/analytics/communication-timeline"],
    ]);
  });

  it("requests a canonical contact timeline when selected", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ summary: {}, months: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await getCommunicationTimeline(42);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/analytics/communication-timeline?canonical_identity_id=42",
    );
  });

  it("requests a chat-specific timeline when selected", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ summary: {}, months: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await getCommunicationTimeline(undefined, 17);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/analytics/communication-timeline?chat_id=17",
    );
  });

  it("lists, links, and unlinks platform identities", async () => {
    const response = {
      identities: [],
      contacts_without_identity: [],
      events: [],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => response,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "linked", identity_group_id: 9 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "unlinked", identity_group_id: null }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getIdentityLinks()).resolves.toEqual(response);
    await expect(linkPlatformIdentities(1, 2)).resolves.toEqual({
      status: "linked",
      identity_group_id: 9,
    });
    await expect(unlinkPlatformIdentity(1)).resolves.toEqual({
      status: "unlinked",
      identity_group_id: null,
    });

    expect(fetchMock.mock.calls[0]).toEqual(["/api/identity-links"]);
    expect(fetchMock.mock.calls[1]).toEqual([
      "/api/identity-links",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          first_identity_id: 1,
          second_identity_id: 2,
        }),
      },
    ]);
    expect(fetchMock.mock.calls[2]).toEqual([
      "/api/identity-links/1",
      { method: "DELETE" },
    ]);
  });

  it("reports a useful error when the backend cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));

    await expect(getOverview()).rejects.toThrow(
      "Unable to connect to the analytics API. Check that the backend is running.",
    );
  });

  it("reports non-success HTTP responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    );

    await expect(getChats()).rejects.toThrow(
      "The analytics API returned an error (HTTP 503).",
    );
  });

  it("reports invalid JSON responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => {
          throw new SyntaxError("invalid JSON");
        },
      }),
    );

    await expect(getContacts()).rejects.toThrow(
      "The analytics API returned an invalid response.",
    );
  });

  it("uploads one file as multipart form data and returns its job", async () => {
    const file = new File(["synthetic export"], "export.json", {
      type: "application/json",
    });
    const job = { id: 17, filename: "export.json", status: "pending" };
    const request = mockUploadRequest(job);
    const onProgress = vi.fn();

    await expect(uploadFile(file, "telegram", onProgress)).resolves.toEqual(job);

    expect(request.open).toHaveBeenCalledWith("POST", "/api/uploads/upload");
    expect(request.send).toHaveBeenCalledTimes(1);
    const [body] = request.send.mock.calls[0];
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("file")).toBe(file);
    expect(body.get("platform")).toBe("telegram");

    request.upload.onprogress?.(
      new ProgressEvent("progress", {
        lengthComputable: true,
        loaded: 25,
        total: 100,
      }),
    );
    expect(onProgress).toHaveBeenCalledWith({
      loadedBytes: 25,
      totalBytes: 100,
    });

    request.upload.onprogress?.(
      new ProgressEvent("progress", {
        lengthComputable: false,
        loaded: 50,
        total: 0,
      }),
    );
    expect(onProgress).toHaveBeenLastCalledWith({ loadedBytes: 50 });
  });

  it("includes the selected platform for an Instagram archive", async () => {
    const file = new File(["synthetic archive"], "instagram.zip", {
      type: "application/zip",
    });
    const request = mockUploadRequest({ id: 18, filename: "instagram.zip" });

    await uploadFile(file, "instagram");

    const [body] = request.send.mock.calls[0];
    expect(body.get("file")).toBe(file);
    expect(body.get("platform")).toBe("instagram");
  });

  it("returns the duplicate upload warning with an accepted job", async () => {
    mockUploadRequest({
      id: 42,
      filename: "duplicate.json",
      warning_message: "This file has already been uploaded",
    });

    await expect(
      uploadFile(
        new File(["synthetic export"], "duplicate.json"),
        "telegram",
      ),
    ).resolves.toMatchObject({
      id: 42,
      warning_message: "This file has already been uploaded",
    });
  });

  it("preserves upload API error details", async () => {
    mockUploadRequest({ detail: "Unsupported export format." }, 422);

    await expect(
      uploadFile(new File(["synthetic export"], "export.json"), "telegram"),
    ).rejects.toThrow("Unsupported export format.");
  });

  it("retries dispatch for a previously accepted upload job", async () => {
    const job = {
      id: 17,
      filename: "export.json",
      status: "pending",
      airflow_dag_run_id: "upload_job_17",
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => job,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(retryUploadJob(17)).resolves.toEqual(job);
    expect(fetchMock).toHaveBeenCalledWith("/api/uploads/jobs/17/retry", {
      method: "POST",
    });
  });

  it("requests DAG and task-instance status for an upload job", async () => {
    const status = {
      id: 17,
      filename: "export.json",
      platform: "telegram",
      status: "processing",
      source_account_id: null,
      import_session_id: null,
      airflow_dag_run_id: "upload_job_17",
      started_at: null,
      finished_at: null,
      error_message: null,
      warning_message: null,
      created_at: "2026-10-22T12:00:00Z",
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
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => status,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getUploadJobStatus(17)).resolves.toEqual(status);

    expect(fetchMock).toHaveBeenCalledWith("/api/uploads/jobs/17/status");
  });
});
