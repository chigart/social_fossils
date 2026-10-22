import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  balance,
  chats,
  contacts,
  forgotten,
  overview,
  timeline,
} from "./App.testFixtures";
import {
  renderLoadedDashboard,
  rowTitles,
  selectDashboardTab,
} from "./App.testUtils";
import App from "./App";

const api = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getChats: vi.fn(),
  getContacts: vi.fn(),
  getCommunicationBalance: vi.fn(),
  getForgottenContacts: vi.fn(),
  getCommunicationTimeline: vi.fn(),
  uploadFile: vi.fn(),
}));

vi.mock("./api", () => api);

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  Object.values(api).forEach((mock) => mock.mockReset());
  api.getOverview.mockResolvedValue(overview);
  api.getChats.mockResolvedValue(chats);
  api.getContacts.mockResolvedValue(contacts);
  api.getCommunicationBalance.mockResolvedValue(balance);
  api.getForgottenContacts.mockResolvedValue(forgotten);
  api.getCommunicationTimeline.mockResolvedValue(timeline);
});

describe("dashboard", () => {
  it("opens the multi-file uploader from the Import tab", async () => {
    await renderLoadedDashboard();
    await selectDashboardTab("Import");

    expect(
      screen.getByRole("heading", { name: "Import files" }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Choose Telegram JSON files"),
    ).toHaveAttribute("multiple");
  });

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
    await selectDashboardTab("Chats");
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

    await selectDashboardTab("Contacts");
    const contactsRegion = screen.getByRole("region", {
      name: "Contacts & senders",
    });
    const combinedContactRows = within(contactsRegion).getAllByRole("row", {
      name: /Avery/,
    });
    expect(combinedContactRows).toHaveLength(1);
    expect(combinedContactRows[0]).toHaveTextContent("@anton, Anton Malkov");
    expect(combinedContactRows[0]).toHaveTextContent("24");
    await selectDashboardTab("Overview");
    const sourceAccountsCard = within(
      screen.getByRole("tabpanel", { name: "Overview" }),
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
    expect(screen.getAllByRole("tab")).toHaveLength(7);
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: "Timeline" })).toHaveAttribute(
      "aria-controls",
      "communication-timeline-panel",
    );
    expect(screen.getByRole("tab", { name: "Import" })).toHaveAttribute(
      "aria-controls",
      "uploads-panel",
    );
    expect(screen.getByText("All messages")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Overview" })).getByText(
        "Ordinary messages",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Overview" })).getByText(
        "Service events",
      ),
    ).toBeInTheDocument();

    await selectDashboardTab("Chats");
    expect(screen.getByRole("heading", { name: "Chats" })).toBeInTheDocument();
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

    await selectDashboardTab("Contacts");
    expect(screen.getByText("Known contact")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Contacts & senders" }))
        .getByRole("columnheader", { name: "Accounts" }),
    ).toBeInTheDocument();
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
    await selectDashboardTab("Balance");
    expect(
      screen.getByRole("heading", { name: "Communication balance" }),
    ).toBeInTheDocument();
    await selectDashboardTab("Forgotten");
    expect(
      screen.getByRole("heading", { name: "Forgotten contacts" }),
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
    api.getCommunicationTimeline.mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getAllByRole("status")).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent("Loading analytics…");
  });

  it("supports keyboard tab navigation and keeps inactive sections hidden", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();

    const overviewTab = screen.getByRole("tab", { name: "Overview" });
    await user.click(overviewTab);
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: "Chats" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(window.location.hash).toBe("#chats");
    expect(screen.getByRole("tabpanel", { name: "Chats" })).not.toHaveAttribute(
      "hidden",
    );
    expect(document.getElementById("overview-panel")).toHaveAttribute("hidden");
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
    await selectDashboardTab("Contacts");
    expect(
      screen.getByText("Import messages to see incoming communication by sender."),
    ).toBeInTheDocument();
    await selectDashboardTab("Forgotten");
    expect(
      screen.getByRole("heading", { name: "No imported data yet" }),
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

    await selectDashboardTab("Chats");
    expect(await screen.findByRole("heading", { name: "No chats available" })).toBeInTheDocument();
    expect(
      screen.getByText("No chats were included in the imported account data."),
    ).toBeInTheDocument();
    await selectDashboardTab("Contacts");
    expect(
      screen.getByText("There are no incoming sender groups in the available analytics."),
    ).toBeInTheDocument();
  });

  it("filters chats and contacts by case-insensitive, trimmed search text", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();

    await selectDashboardTab("Chats");
    await user.type(
      screen.getByRole("searchbox", { name: "Search chats by title" }),
      "  AURORA ",
    );
    const chatsRegion = screen.getByRole("region", { name: "Chats" });
    expect(within(chatsRegion).getByRole("row", { name: /Aurora group/ })).toBeInTheDocument();
    expect(within(chatsRegion).queryByRole("row", { name: /Zebra group/ })).not.toBeInTheDocument();

    await selectDashboardTab("Contacts");
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
    await selectDashboardTab("Chats");

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
    await selectDashboardTab("Chats");
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
    await selectDashboardTab("Contacts");
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
    await selectDashboardTab("Chats");
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
    await selectDashboardTab("Contacts");
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

  it("shows ranked Forgotten Contacts with monthly activity, evidence, and filtering", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    await selectDashboardTab("Forgotten");

    const region = screen.getByRole("region", { name: "Forgotten contacts" });
    expect(within(region).getByText(/Scope: Combined owner data/)).toBeInTheDocument();
    expect(
      within(region).getByRole("columnheader", { name: "Monthly activity" }),
    ).toBeInTheDocument();
    expect(
      within(region).getAllByRole("img", { name: /Historical monthly activity/ }),
    ).toHaveLength(forgotten.contacts.length);
    expect(within(region).getAllByText("Inactive")).toHaveLength(2);
    expect(within(region).getAllByText("Reliable baseline")).toHaveLength(
      forgotten.contacts.length,
    );
    expect(within(region).getByText(/descriptive heuristics/)).toBeInTheDocument();

    const table = within(region).getByRole("table");
    expect(rowTitles(table)).toEqual(["Mika", "Zoe", "Lena"]);

    await user.click(within(region).getByRole("button", { name: "Sort by Name" }));
    expect(rowTitles(table)).toEqual(["Lena", "Mika", "Zoe"]);
    await user.type(
      within(region).getByRole("searchbox", { name: "Search forgotten contacts" }),
      "zoe",
    );
    expect(rowTitles(table)).toEqual(["Zoe"]);
  });

  it("shows insufficient-history evidence and a no-match state", async () => {
    const user = userEvent.setup();
    api.getForgottenContacts.mockResolvedValue({
      ...forgotten,
      summary: {
        ...forgotten.summary,
        insufficient_data_contacts: 1,
      },
      contacts: [
        {
          ...forgotten.contacts[0],
          classification: "insufficient_data",
          evidence_status: "insufficient_history",
          ranking_score: null,
        },
      ],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Forgotten");

    const region = screen.getByRole("region", { name: "Forgotten contacts" });
    expect(
      within(region).getByText(/insufficient history or ambiguous message direction/),
    ).toBeInTheDocument();
    expect(within(region).getByText("Insufficient history")).toBeInTheDocument();
    await user.type(
      within(region).getByRole("searchbox", { name: "Search forgotten contacts" }),
      "nobody",
    );
    expect(
      within(region).getByText("No contacts match the selected search."),
    ).toBeInTheDocument();
  });

  it("shows a distinct no-eligible-contact state after imports exist", async () => {
    api.getForgottenContacts.mockResolvedValue({
      ...forgotten,
      summary: {
        ...forgotten.summary,
        eligible_contacts: 0,
        meaningful_historical_contacts: 0,
        currently_inactive_contacts: 0,
        declining_activity_contacts: 0,
        insufficient_data_contacts: 0,
      },
      contacts: [],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Forgotten");

    const region = screen.getByRole("region", { name: "Forgotten contacts" });
    expect(
      within(region).getByRole("heading", {
        name: "No eligible contacts available",
      }),
    ).toBeInTheDocument();
    expect(
      within(region).getByText(
        "No identifiable one-to-one contacts are available for comparison.",
      ),
    ).toBeInTheDocument();
  });

  it("retries a failed Forgotten Contacts request", async () => {
    const user = userEvent.setup();
    api.getForgottenContacts.mockRejectedValueOnce(
      new Error("Forgotten contacts unavailable."),
    );
    render(<App />);
    await selectDashboardTab("Forgotten");

    const region = screen.getByRole("region", { name: "Forgotten contacts" });
    expect(await within(region).findByRole("alert")).toHaveTextContent(
      "Forgotten contacts unavailable.",
    );
    await user.click(within(region).getByRole("button", { name: "Retry" }));
    expect(await within(region).findByText("Mika")).toBeInTheDocument();
    expect(api.getForgottenContacts).toHaveBeenCalledTimes(2);
  });

  it("plots monthly totals and loads a canonical contact timeline on selection", async () => {
    const user = userEvent.setup();
    api.getCommunicationTimeline
      .mockResolvedValueOnce(timeline)
      .mockResolvedValueOnce({
        ...timeline,
        summary: {
          ...timeline.summary,
          scope: "contact",
          canonical_identity_id: 1,
          source_contact_ids: [11],
        },
      });
    await renderLoadedDashboard();
    await selectDashboardTab("Timeline");

    const region = screen.getByRole("region", {
      name: "Communication timeline",
    });
    const chart = within(region).getByRole("img", {
      name: "Monthly ordinary message activity",
    });
    expect(chart.querySelector('[data-month="2023-02"][data-count="0"]')).toBeTruthy();
    expect(chart.querySelector('[data-month="2023-03"][data-count="2"]')).toBeTruthy();
    expect(
      within(region).getByRole("list", {
        name: "Monthly communication activity details",
      }),
    ).toHaveTextContent("unknown direction");
    expect(
      within(region).getByText("Combined owner history", { selector: "strong" }),
    ).toBeInTheDocument();
    expect(within(region).getByText(/@anton/)).toBeInTheDocument();

    await user.selectOptions(
      within(region).getByRole("combobox", { name: "Timeline scope" }),
      "1",
    );

    expect(api.getCommunicationTimeline).toHaveBeenNthCalledWith(2, 1);
    expect(await within(region).findByText("Avery")).toBeInTheDocument();
  });

  it("shows timeline retry errors and undated-only empty states", async () => {
    const user = userEvent.setup();
    api.getCommunicationTimeline
      .mockRejectedValueOnce(new Error("Timeline unavailable."))
      .mockResolvedValueOnce({
        ...timeline,
        summary: {
          ...timeline.summary,
          ordinary_message_count: 2,
          dated_ordinary_message_count: 0,
          undated_ordinary_message_count: 2,
        },
        months: [],
      });
    render(<App />);
    await selectDashboardTab("Timeline");

    const region = screen.getByRole("region", {
      name: "Communication timeline",
    });
    expect(await within(region).findByRole("alert")).toHaveTextContent(
      "Timeline unavailable.",
    );
    await user.click(within(region).getByRole("button", { name: "Retry" }));
    expect(
      await within(region).findByRole("heading", {
        name: "No dated ordinary messages",
      }),
    ).toBeInTheDocument();
    expect(
      within(region).getByText(/2 ordinary messages have no reliable timestamp/),
    ).toBeInTheDocument();
  });
});
