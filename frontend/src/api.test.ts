import { describe, expect, it, vi } from "vitest";
import {
  getChats,
  getCommunicationBalance,
  getCommunicationTimeline,
  getContacts,
  getForgottenContacts,
  getOverview,
  uploadFile,
} from "./api";

describe("analytics API helpers", () => {
  it("requests each analytics endpoint and returns its JSON data", async () => {
    const overview = { total_messages: 17 };
    const chats = [{ chat_id: 1 }];
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

    await expect(uploadFile(file)).resolves.toEqual(job);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [path, options] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/uploads/upload");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect((options.body as FormData).get("file")).toBe(file);
  });

  it("uses the server error detail for a rejected file", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: "This file has already been uploaded" }),
      }),
    );

    await expect(
      uploadFile(new File(["synthetic export"], "duplicate.json")),
    ).rejects.toThrow("This file has already been uploaded");
  });
});
