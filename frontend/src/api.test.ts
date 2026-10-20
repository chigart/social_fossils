import { describe, expect, it, vi } from "vitest";
import { getChats, getContacts, getOverview } from "./api";

describe("analytics API helpers", () => {
  it("requests each analytics endpoint and returns its JSON data", async () => {
    const overview = { total_messages: 17 };
    const chats = [{ chat_id: 1 }];
    const contacts = [{ account_id: 2 }];
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
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getOverview()).resolves.toEqual(overview);
    await expect(getChats()).resolves.toEqual(chats);
    await expect(getContacts()).resolves.toEqual(contacts);

    expect(fetchMock.mock.calls).toEqual([
      ["/api/analytics/overview"],
      ["/api/analytics/chats"],
      ["/api/analytics/contacts"],
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
});
