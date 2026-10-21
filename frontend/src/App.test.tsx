import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ChatStatistics,
  CommunicationBalanceStatistics,
  ContactStatistics,
  OverviewStatistics,
} from "./api";
import App from "./App";

const api = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getChats: vi.fn(),
  getContacts: vi.fn(),
  getCommunicationBalance: vi.fn(),
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
    account_id: 1,
    source_account_label: "@anton",
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
    account_id: 1,
    source_account_label: "@anton",
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
    account_id: 1,
    source_account_label: "@anton",
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
    canonical_identity_id: 1,
    source_account_ids: [1],
    source_account_labels: ["@anton"],
    source_contact_ids: [11],
    telegram_user_id: "12345",
    display_name: "Avery",
    total_messages_sent: 12,
    ordinary_messages_sent: 11,
    service_events_attributed: 1,
  },
  {
    account_id: 1,
    contact_id: null,
    canonical_identity_id: null,
    source_account_ids: [1],
    source_account_labels: ["@anton"],
    source_contact_ids: [],
    telegram_user_id: "67890",
    display_name: "Morgan",
    total_messages_sent: 5,
    ordinary_messages_sent: 4,
    service_events_attributed: 1,
  },
  {
    account_id: 1,
    contact_id: null,
    canonical_identity_id: null,
    source_account_ids: [1],
    source_account_labels: ["@anton"],
    source_contact_ids: [],
    telegram_user_id: null,
    display_name: null,
    total_messages_sent: 2,
    ordinary_messages_sent: 2,
    service_events_attributed: 0,
  },
];

const emptyBalanceSummary = {
  eligible_contacts: 0,
  balanced_contacts: 0,
  mostly_owner_contacts: 0,
  mostly_contact_contacts: 0,
  strongly_owner_contacts: 0,
  strongly_contact_contacts: 0,
  insufficient_data_contacts: 0,
  owner_text_length: 0,
  contact_text_length: 0,
  total_text_length: 0,
  owner_message_count: 0,
  contact_message_count: 0,
  total_message_count: 0,
  excluded_unknown_direction_message_count: 0,
};

const balance: CommunicationBalanceStatistics = {
  summary: {
    ...emptyBalanceSummary,
    eligible_contacts: 5,
    balanced_contacts: 1,
    mostly_owner_contacts: 1,
    mostly_contact_contacts: 1,
    strongly_owner_contacts: 1,
    insufficient_data_contacts: 1,
    owner_text_length: 1_900,
    contact_text_length: 1_800,
    total_text_length: 3_700,
    owner_message_count: 9,
    contact_message_count: 8,
    total_message_count: 17,
  },
  contacts: [
    {
      account_id: 1,
      contact_id: 21,
      canonical_identity_id: 21,
      source_account_ids: [1],
      source_account_labels: ["@anton"],
      source_contact_ids: [21],
      telegram_user_id: "user-alex",
      display_name: "Alex",
      owner_message_count: 1,
      contact_message_count: 5,
      total_message_count: 6,
      excluded_unknown_direction_message_count: 0,
      owner_text_length: 500,
      contact_text_length: 500,
      total_text_length: 1_000,
      owner_text_share: 0.5,
      contact_text_share: 0.5,
      absolute_share_difference: 0,
      owner_share_percentage: 50,
      contact_share_percentage: 50,
      classification: "balanced",
      first_message_at: "2025-01-01T12:00:00Z",
      last_message_at: "2025-01-10T12:00:00Z",
      distinct_active_days: 2,
    },
    {
      account_id: 1,
      contact_id: 22,
      canonical_identity_id: 22,
      source_account_ids: [1],
      source_account_labels: ["@anton"],
      source_contact_ids: [22],
      telegram_user_id: "user-bea",
      display_name: "Bea",
      owner_message_count: 8,
      contact_message_count: 1,
      total_message_count: 9,
      excluded_unknown_direction_message_count: 0,
      owner_text_length: 490,
      contact_text_length: 210,
      total_text_length: 700,
      owner_text_share: 0.7,
      contact_text_share: 0.3,
      absolute_share_difference: 0.4,
      owner_share_percentage: 70,
      contact_share_percentage: 30,
      classification: "mostly_owner",
      first_message_at: "2025-02-01T12:00:00Z",
      last_message_at: "2025-02-10T12:00:00Z",
      distinct_active_days: 2,
    },
    {
      account_id: 1,
      contact_id: 23,
      canonical_identity_id: 23,
      source_account_ids: [1],
      source_account_labels: ["@anton"],
      source_contact_ids: [23],
      telegram_user_id: "user-cora",
      display_name: "Cora",
      owner_message_count: 3,
      contact_message_count: 3,
      total_message_count: 6,
      excluded_unknown_direction_message_count: 0,
      owner_text_length: 300,
      contact_text_length: 900,
      total_text_length: 1_200,
      owner_text_share: 0.25,
      contact_text_share: 0.75,
      absolute_share_difference: 0.5,
      owner_share_percentage: 25,
      contact_share_percentage: 75,
      classification: "mostly_contact",
      first_message_at: "2025-03-01T12:00:00Z",
      last_message_at: "2025-03-15T12:00:00Z",
      distinct_active_days: 4,
    },
    {
      account_id: 1,
      contact_id: 24,
      canonical_identity_id: 24,
      source_account_ids: [1],
      source_account_labels: ["@anton"],
      source_contact_ids: [24],
      telegram_user_id: "user-zero",
      display_name: "Zero text",
      owner_message_count: 2,
      contact_message_count: 2,
      total_message_count: 4,
      excluded_unknown_direction_message_count: 0,
      owner_text_length: 0,
      contact_text_length: 0,
      total_text_length: 0,
      owner_text_share: null,
      contact_text_share: null,
      absolute_share_difference: null,
      owner_share_percentage: null,
      contact_share_percentage: null,
      classification: "insufficient_data",
      first_message_at: null,
      last_message_at: null,
      distinct_active_days: 0,
    },
    {
      account_id: 1,
      contact_id: 25,
      canonical_identity_id: 25,
      source_account_ids: [1],
      source_account_labels: ["@anton"],
      source_contact_ids: [25],
      telegram_user_id: "user-drew",
      display_name: "Drew",
      owner_message_count: 1,
      contact_message_count: 1,
      total_message_count: 2,
      excluded_unknown_direction_message_count: 0,
      owner_text_length: 900,
      contact_text_length: 100,
      total_text_length: 1_000,
      owner_text_share: 0.9,
      contact_text_share: 0.1,
      absolute_share_difference: 0.8,
      owner_share_percentage: 90,
      contact_share_percentage: 10,
      classification: "strongly_owner",
      first_message_at: "2025-04-01T12:00:00Z",
      last_message_at: "2025-04-01T12:00:00Z",
      distinct_active_days: 1,
    },
  ],
};

beforeEach(() => {
  api.getOverview.mockResolvedValue(overview);
  api.getChats.mockResolvedValue(chats);
  api.getContacts.mockResolvedValue(contacts);
  api.getCommunicationBalance.mockResolvedValue(balance);
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
  it("shows multiple accounts by username with full-name fallback and combines contacts", async () => {
    api.getOverview.mockResolvedValue({
      ...overview,
      total_imported_accounts: 2,
      total_chats: 2,
      total_messages: 70,
    });
    api.getChats.mockResolvedValue([
      {
        ...chats[0],
        chat_id: 101,
        account_id: 1,
        source_account_label: "@anton",
        title: "First account chat",
        total_messages: 30,
      },
      {
        ...chats[1],
        chat_id: 202,
        account_id: 2,
        source_account_label: "Anton Malkov",
        title: "Second account chat",
        total_messages: 40,
      },
    ]);
    api.getContacts.mockResolvedValue([
      {
        ...contacts[0],
        account_id: null,
        canonical_identity_id: 501,
        contact_id: 11,
        source_account_ids: [1, 2],
        source_account_labels: ["@anton", "Anton Malkov"],
        source_contact_ids: [11, 22],
        total_messages_sent: 24,
        ordinary_messages_sent: 22,
        service_events_attributed: 2,
      },
    ]);

    render(<App />);
    await screen.findByRole("row", { name: /First account chat/ });

    const chatRegion = screen.getByRole("region", { name: "Chats" });
    expect(
      within(chatRegion).getByRole("row", {
        name: /First account chat.*@anton/,
      }),
    ).toBeInTheDocument();
    expect(
      within(chatRegion).getByRole("row", {
        name: /Second account chat.*Anton Malkov/,
      }),
    ).toBeInTheDocument();

    const contactsRegion = screen.getByRole("region", {
      name: "Contacts & senders",
    });
    const combinedContactRows = within(contactsRegion).getAllByRole("row", {
      name: /Avery/,
    });
    expect(combinedContactRows).toHaveLength(1);
    expect(combinedContactRows[0]).toHaveTextContent("@anton, Anton Malkov");
    expect(combinedContactRows[0]).toHaveTextContent("24");
    const sourceAccountsCard = within(
      screen.getByRole("region", { name: "Overview" }),
    )
      .getByRole("heading", { name: "Source accounts" })
      .closest("article");
    expect(sourceAccountsCard).toHaveTextContent("2");
  });

  it("shows the dashboard content, aggregate metrics, and sender link states", async () => {
    await renderLoadedDashboard();

    expect(
      screen.getByRole("heading", { name: "Your communication, in context." }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Combined account data/)).toBeInTheDocument();
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
    expect(screen.getByRole("link", { name: "Balance" })).toHaveAttribute(
      "href",
      "#communication-balance",
    );
    expect(screen.getByText("All messages")).toBeInTheDocument();
    expect(screen.getByText("Ordinary messages")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Overview" })).getByText(
        "Service events",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Known contact")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Contacts & senders" }))
        .getByRole("columnheader", { name: "Accounts" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Chats" })).getByRole(
        "columnheader",
        { name: "Account" },
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Chats" })).getAllByText(
        "@anton",
      ),
    ).toHaveLength(chats.length);
    expect(
      within(screen.getByRole("region", { name: "Contacts & senders" })).getByRole(
        "row",
        { name: /Avery.*@anton/ },
      ),
    ).toBeInTheDocument();
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

  it("shows loading status while all analytics requests are pending", () => {
    api.getOverview.mockReturnValue(new Promise(() => {}));
    api.getChats.mockReturnValue(new Promise(() => {}));
    api.getContacts.mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getAllByRole("status")).toHaveLength(4);
    expect(screen.getAllByText("Loading analytics…")).toHaveLength(4);
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

  it("retries a failed communication balance request without crashing other sections", async () => {
    const user = userEvent.setup();
    api.getCommunicationBalance.mockRejectedValueOnce(
      new Error("Balance analytics unavailable."),
    );
    render(<App />);
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });

    expect(await within(balanceRegion).findByRole("alert")).toHaveTextContent(
      "Balance analytics unavailable.",
    );
    expect(
      screen.getByRole("region", { name: "Overview" }),
    ).toBeInTheDocument();
    await user.click(within(balanceRegion).getByRole("button", { name: "Retry" }));

    expect(
      await within(balanceRegion).findByRole("row", { name: /Alex/ }),
    ).toBeInTheDocument();
    expect(api.getCommunicationBalance).toHaveBeenCalledTimes(2);
  });

  it("shows the eligible-contact empty state when the API has no results", async () => {
    api.getCommunicationBalance.mockResolvedValue({
      summary: emptyBalanceSummary,
      contacts: [],
    });
    render(<App />);

    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    expect(
      await within(balanceRegion).findByRole("heading", {
        name: "No eligible contacts available",
      }),
    ).toBeInTheDocument();
    expect(
      within(balanceRegion).getByText("Eligible contacts").parentElement,
    ).toHaveTextContent("0");
  });

  it("renders summary values directly from the communication balance API", async () => {
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });

    for (const [label, value] of [
      ["Eligible contacts", "5"],
      ["Balanced", "1"],
      ["Mostly owner", "1"],
      ["Mostly contact", "1"],
      ["Strongly owner", "1"],
      ["Strongly contact", "0"],
      ["Insufficient data", "1"],
      ["Total text exchanged", "3,700"],
    ]) {
      expect(
        within(balanceRegion).getByText(label, { selector: "h3" }).parentElement,
      ).toHaveTextContent(value);
    }
  });

  it("shows text volume, API shares, date values, and supplementary message counts", async () => {
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const alexRow = within(balanceRegion).getByRole("row", { name: /Alex/ });

    expect(alexRow).toHaveTextContent("1,000");
    expect(alexRow).toHaveTextContent("500");
    expect(alexRow).toHaveTextContent("Balanced");
    expect(alexRow).toHaveTextContent("1");
    expect(alexRow).toHaveTextContent("5");
    const alexShare = within(alexRow).getByRole("img", {
      name: "Owner 50%, contact 50%",
    });
    const alexBar = alexShare.querySelectorAll(".flex")[1];
    expect(alexBar?.children[0]).toHaveStyle({ width: "50%" });
    expect(alexBar?.children[1]).toHaveStyle({ width: "50%" });

    const coraRow = within(balanceRegion).getByRole("row", { name: /Cora/ });
    const coraShare = within(coraRow).getByRole("img", {
      name: "Owner 25%, contact 75%",
    });
    const coraBar = coraShare.querySelectorAll(".flex")[1];
    expect(coraBar?.children[0]).toHaveStyle({ width: "25%" });
    expect(coraBar?.children[1]).toHaveStyle({ width: "75%" });
    expect(
      balanceRegion,
    ).toHaveTextContent("Text volume counts Unicode code points");
    expect(balanceRegion).toHaveTextContent("First seen");
    expect(balanceRegion).toHaveTextContent("Last seen");
  });

  it("filters contacts by API classification and searches display names", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const classificationFilter = within(balanceRegion).getByRole("combobox", {
      name: "Filter by classification",
    });

    await user.selectOptions(classificationFilter, "mostly_owner");
    expect(within(balanceRegion).getAllByRole("row")).toHaveLength(2);
    expect(within(balanceRegion).getByRole("row", { name: /Bea/ })).toBeInTheDocument();
    expect(within(balanceRegion).queryByRole("row", { name: /Alex/ })).not.toBeInTheDocument();

    await user.selectOptions(classificationFilter, "all");
    const search = within(balanceRegion).getByRole("searchbox", {
      name: "Search balance contacts by display name",
    });
    await user.type(search, "  cOrA ");
    expect(within(balanceRegion).getAllByRole("row")).toHaveLength(2);
    expect(within(balanceRegion).getByRole("row", { name: /Cora/ })).toBeInTheDocument();
  });

  it("sorts by total text volume, not message counts", async () => {
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const sortBy = within(balanceRegion).getByRole("combobox", {
      name: "Sort contacts by",
    });
    const table = within(balanceRegion).getByRole("table");

    expect(rowTitles(table)).toEqual([
      "Cora",
      "Alex",
      "Drew",
      "Bea",
      "Zero text",
    ]);
    await userEvent.setup().selectOptions(sortBy, "owner_share");
    expect(rowTitles(table)).toEqual([
      "Drew",
      "Bea",
      "Alex",
      "Cora",
      "Zero text",
    ]);
  });

  it("sorts owner text share in the selected direction and keeps missing shares last", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    await user.selectOptions(
      within(balanceRegion).getByRole("combobox", { name: "Sort contacts by" }),
      "owner_share",
    );
    await user.selectOptions(
      within(balanceRegion).getByRole("combobox", { name: "Sort direction" }),
      "asc",
    );

    expect(rowTitles(within(balanceRegion).getByRole("table"))).toEqual([
      "Cora",
      "Alex",
      "Bea",
      "Drew",
      "Zero text",
    ]);
  });

  it("sorts most recent activity with undated contacts last", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    await user.selectOptions(
      within(balanceRegion).getByRole("combobox", { name: "Sort contacts by" }),
      "recent_activity",
    );

    expect(rowTitles(within(balanceRegion).getByRole("table"))).toEqual([
      "Drew",
      "Cora",
      "Bea",
      "Alex",
      "Zero text",
    ]);
  });

  it("marks insufficient-data contacts distinctly and avoids invalid zero-volume shares", async () => {
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const zeroRow = within(balanceRegion).getByRole("row", { name: /Zero text/ });

    expect(zeroRow).toHaveTextContent("Insufficient data");
    expect(zeroRow).toHaveTextContent("Less than 500 characters");
    expect(zeroRow).toHaveTextContent("No text volume to compare");
    expect(zeroRow).toHaveTextContent("Owner — · Contact —");
    expect(zeroRow).not.toHaveTextContent("NaN");
    expect(zeroRow).not.toHaveTextContent("Infinity");
  });

  it("keeps the balance table scrollable and controls usable on narrow screens", async () => {
    await renderLoadedDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const table = within(balanceRegion).getByRole("table");

    expect(table).toHaveClass("min-w-[1050px]");
    expect(
      within(balanceRegion).getByRole("region", {
        name: "Scrollable communication balance table",
      }),
    ).toHaveClass("overflow-x-scroll");
    expect(
      within(balanceRegion).getByText(
        "The table is wider than this panel. Scroll horizontally to see the remaining columns.",
      ),
    ).toBeInTheDocument();
    expect(
      within(balanceRegion).getByRole("combobox", { name: "Sort direction" }),
    ).toBeVisible();
    expect(
      within(balanceRegion).getByRole("searchbox", {
        name: "Search balance contacts by display name",
      }),
    ).toBeVisible();
  });
});
