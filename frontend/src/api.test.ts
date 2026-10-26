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
  linkPlatformIdentities,
  retryUploadJob,
  unlinkPlatformIdentity,
  uploadFile,
} from "./api";

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
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => job,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(uploadFile(file, "telegram")).resolves.toEqual(job);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [path, options] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/uploads/upload");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect((options.body as FormData).get("file")).toBe(file);
    expect((options.body as FormData).get("platform")).toBe("telegram");
  });

  it("includes the selected platform for an Instagram archive", async () => {
    const file = new File(["synthetic archive"], "instagram.zip", {
      type: "application/zip",
    });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 18, filename: "instagram.zip" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await uploadFile(file, "instagram");

    const [, options] = fetchMock.mock.calls[0];
    expect((options.body as FormData).get("file")).toBe(file);
    expect((options.body as FormData).get("platform")).toBe("instagram");
  });

  it("returns the duplicate upload warning with an accepted job", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: 42,
          filename: "duplicate.json",
          warning_message: "This file has already been uploaded",
        }),
      }),
    );

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
});
