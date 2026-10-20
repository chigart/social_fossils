import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ChatStatistics,
  ContactStatistics,
  OverviewStatistics,
} from "./api";
import App from "./App";

const api = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getChats: vi.fn(),
  getContacts: vi.fn(),
}));

vi.mock("./api", () => api);

const overview: OverviewStatistics = {
  total_imported_accounts: 1,
  total_chats: 3,
  total_messages: 35,
  total_ordinary_messages: 31,
  total_service_messages: 4,
  earliest_message_timestamp: "2022-01-01T12:00:00Z",
  latest_message_timestamp: "2024-03-15T12:30:00Z",
};

const chats: ChatStatistics[] = [
  {
    chat_id: 1,
    telegram_chat_id: "1001",
    title: "Zebra group",
    chat_type: "group",
    total_messages: 9,
    ordinary_messages: 8,
    service_messages: 1,
    earliest_message_timestamp: "2022-01-01T12:00:00Z",
    latest_message_timestamp: "2023-01-01T12:00:00Z",
    distinct_identified_senders: 2,
  },
  {
    chat_id: 2,
    telegram_chat_id: "1002",
    title: "Aurora group",
    chat_type: "group",
    total_messages: 24,
    ordinary_messages: 22,
    service_messages: 2,
    earliest_message_timestamp: "2022-02-01T12:00:00Z",
    latest_message_timestamp: "2024-03-15T12:30:00Z",
    distinct_identified_senders: 3,
  },
  {
    chat_id: 3,
    telegram_chat_id: "1003",
    title: null,
    chat_type: "private",
    total_messages: 2,
    ordinary_messages: 1,
    service_messages: 1,
    earliest_message_timestamp: null,
    latest_message_timestamp: null,
    distinct_identified_senders: 1,
  },
];

const contacts: ContactStatistics[] = [
  {
    account_id: 1,
    contact_id: 11,
    telegram_user_id: "12345",
    display_name: "Avery",
    total_messages_sent: 12,
    ordinary_messages_sent: 11,
    service_events_attributed: 1,
  },
  {
    account_id: 1,
    contact_id: null,
    telegram_user_id: "67890",
    display_name: "Morgan",
    total_messages_sent: 5,
    ordinary_messages_sent: 4,
    service_events_attributed: 1,
  },
  {
    account_id: 1,
    contact_id: null,
    telegram_user_id: null,
    display_name: null,
    total_messages_sent: 2,
    ordinary_messages_sent: 2,
    service_events_attributed: 0,
  },
];

beforeEach(() => {
  api.getOverview.mockResolvedValue(overview);
  api.getChats.mockResolvedValue(chats);
  api.getContacts.mockResolvedValue(contacts);
});

async function renderLoadedDashboard() {
  render(<App />);
  await screen.findByRole("row", { name: /Aurora group/ });
}

function rowTitles(table: HTMLElement) {
  const body = table.querySelector("tbody");
  if (!body) throw new Error("Expected the table to contain a body.");

  return within(body)
    .getAllByRole("row")
    .map((row) => within(row).getByRole("rowheader").textContent);
}

describe("dashboard", () => {
  it("shows the dashboard content, aggregate metrics, and sender link states", async () => {
    await renderLoadedDashboard();

    expect(
      screen.getByRole("heading", { name: "Your communication, in context." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Dashboard sections" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "href",
      "#overview",
    );
    expect(screen.getByRole("link", { name: "Chats" })).toHaveAttribute(
      "href",
      "#chats",
    );
    expect(screen.getByRole("link", { name: "Contacts" })).toHaveAttribute(
      "href",
      "#contacts",
    );
    expect(screen.getByText("All messages")).toBeInTheDocument();
    expect(screen.getByText("Ordinary messages")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Overview" })).getByText(
        "Service events",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Known contact")).toBeInTheDocument();
    expect(screen.getByText("Unlinked sender")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Contacts & senders" })).getByRole(
        "row",
        { name: /Unknown sender/ },
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Statistics are aggregated from imported data. Message contents are not shown.",
      ),
    ).toBeInTheDocument();
  });

  it("shows loading status while the three analytics requests are pending", () => {
    api.getOverview.mockReturnValue(new Promise(() => {}));
    api.getChats.mockReturnValue(new Promise(() => {}));
    api.getContacts.mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getAllByRole("status")).toHaveLength(3);
    expect(screen.getAllByText("Loading analytics…")).toHaveLength(3);
  });

  it("shows the no-import guidance when analytics contain no imported data", async () => {
    api.getOverview.mockResolvedValue({
      ...overview,
      total_imported_accounts: 0,
      total_chats: 0,
      total_messages: 0,
      total_ordinary_messages: 0,
      total_service_messages: 0,
    });
    api.getChats.mockResolvedValue([]);
    api.getContacts.mockResolvedValue([]);
    render(<App />);

    expect(await screen.findByText("No imported data yet.")).toBeInTheDocument();
    expect(
      await screen.findByText("Import a Telegram export to see chat statistics."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Import messages to see incoming communication by sender."),
    ).toBeInTheDocument();
  });

  it("distinguishes empty results from an account with no conversations or incoming senders", async () => {
    api.getOverview.mockResolvedValue({
      ...overview,
      total_chats: 0,
      total_messages: 8,
    });
    api.getChats.mockResolvedValue([]);
    api.getContacts.mockResolvedValue([]);
    render(<App />);

    expect(await screen.findByRole("heading", { name: "No chats available" })).toBeInTheDocument();
    expect(
      screen.getByText("No chats were included in the imported account data."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("There are no incoming sender groups in the available analytics."),
    ).toBeInTheDocument();
  });

  it("filters chats and contacts by case-insensitive, trimmed search text", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();

    await user.type(
      screen.getByRole("searchbox", { name: "Search chats by title" }),
      "  AURORA ",
    );
    const chatsRegion = screen.getByRole("region", { name: "Chats" });
    expect(within(chatsRegion).getByRole("row", { name: /Aurora group/ })).toBeInTheDocument();
    expect(within(chatsRegion).queryByRole("row", { name: /Zebra group/ })).not.toBeInTheDocument();

    const contactsRegion = screen.getByRole("region", { name: "Contacts & senders" });
    await user.type(
      within(contactsRegion).getByRole("searchbox", {
        name: "Search contacts by display name",
      }),
      "  mORGAN ",
    );
    expect(within(contactsRegion).getByRole("row", { name: /Morgan/ })).toBeInTheDocument();
    expect(within(contactsRegion).queryByRole("row", { name: /Avery/ })).not.toBeInTheDocument();

    const contactSearch = within(contactsRegion).getByRole("searchbox", {
      name: "Search contacts by display name",
    });
    await user.clear(contactSearch);
    await user.type(contactSearch, "missing");
    expect(
      await within(contactsRegion).findByText(
        "No display names match “missing”.",
      ),
    ).toBeInTheDocument();
  });

  it("shows a no-match message when a chat search returns no results", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();

    await user.type(
      screen.getByRole("searchbox", { name: "Search chats by title" }),
      "missing",
    );

    expect(
      await screen.findByText("No chats match “missing”. Try a different title."),
    ).toBeInTheDocument();
  });

  it("sorts chats by message count by default and toggles title sort direction", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    const chatsRegion = screen.getByRole("region", { name: "Chats" });
    const chatsTable = within(chatsRegion).getByRole("table");

    expect(rowTitles(chatsTable)).toEqual([
      "Aurora group",
      "Zebra group",
      "Untitled chat",
    ]);

    const titleSort = within(chatsRegion).getByRole("button", {
      name: "Sort by Chat title",
    });
    await user.click(titleSort);
    expect(rowTitles(chatsTable)).toEqual([
      "Untitled chat",
      "Aurora group",
      "Zebra group",
    ]);
    expect(titleSort).toHaveAttribute("aria-label", "Sort by Chat title, ascending");

    await user.click(titleSort);
    expect(rowTitles(chatsTable)).toEqual([
      "Zebra group",
      "Aurora group",
      "Untitled chat",
    ]);
    expect(titleSort).toHaveAttribute("aria-label", "Sort by Chat title, descending");
  });

  it("toggles contact message sorting between ascending and descending", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    const contactsRegion = screen.getByRole("region", { name: "Contacts & senders" });
    const contactsTable = within(contactsRegion).getByRole("table");
    const sortButton = within(contactsRegion).getByRole("button", {
      name: "Sort by Messages sent, descending",
    });

    expect(rowTitles(contactsTable)).toEqual(["Avery", "Morgan", "Unknown sender"]);
    await user.click(sortButton);
    expect(rowTitles(contactsTable)).toEqual(["Unknown sender", "Morgan", "Avery"]);
    expect(sortButton).toHaveAttribute(
      "aria-label",
      "Sort by Messages sent, ascending",
    );
  });

  it("retries a failed chat request and then shows the returned chats", async () => {
    const user = userEvent.setup();
    api.getChats.mockRejectedValueOnce(new Error("Chat analytics unavailable."));
    render(<App />);
    const chatsRegion = screen.getByRole("region", { name: "Chats" });

    expect(await within(chatsRegion).findByRole("alert")).toHaveTextContent(
      "Chat analytics unavailable.",
    );
    await user.click(within(chatsRegion).getByRole("button", { name: "Retry" }));

    expect(
      await within(chatsRegion).findByRole("row", { name: /Aurora group/ }),
    ).toBeInTheDocument();
    expect(api.getChats).toHaveBeenCalledTimes(2);
  });

  it("retries a failed overview request", async () => {
    const user = userEvent.setup();
    api.getOverview.mockRejectedValueOnce(new Error("Overview unavailable."));
    render(<App />);
    const overviewRegion = screen.getByRole("region", { name: "Overview" });

    expect(await within(overviewRegion).findByRole("alert")).toHaveTextContent(
      "Overview unavailable.",
    );
    await user.click(within(overviewRegion).getByRole("button", { name: "Retry" }));

    expect(await within(overviewRegion).findByText("All messages")).toBeInTheDocument();
    expect(api.getOverview).toHaveBeenCalledTimes(2);
  });

  it("shows a fallback message when a request rejects without an Error", async () => {
    api.getOverview.mockRejectedValueOnce("unexpected failure");
    render(<App />);

    expect(
      await within(
        screen.getByRole("region", { name: "Overview" }),
      ).findByText("Unable to load overview statistics."),
    ).toBeInTheDocument();
  });

  it("retries a failed contacts request", async () => {
    const user = userEvent.setup();
    api.getContacts.mockRejectedValueOnce(new Error("Contact analytics unavailable."));
    render(<App />);
    const contactsRegion = screen.getByRole("region", { name: "Contacts & senders" });

    expect(await within(contactsRegion).findByRole("alert")).toHaveTextContent(
      "Contact analytics unavailable.",
    );
    await user.click(within(contactsRegion).getByRole("button", { name: "Retry" }));

    expect(
      await within(contactsRegion).findByRole("row", { name: /Avery/ }),
    ).toBeInTheDocument();
    expect(api.getContacts).toHaveBeenCalledTimes(2);
  });
});
