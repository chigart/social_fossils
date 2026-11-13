import {
  render,
  screen,
  within,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { paginated, resetDashboardApi } from "./dashboardTestHelpers";
import {
  chats,
  forgotten,
  overview,
} from "./App.testFixtures";
import {
  renderLoadedDashboard,
  rowTitles,
  selectDashboardTab,
} from "./App.testUtils";
import App from "../App";

const api = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getChatInsights: vi.fn(),
  getChats: vi.fn(),
  getContacts: vi.fn(),
  getIdentityLinks: vi.fn(),
  linkPlatformIdentities: vi.fn(),
  unlinkPlatformIdentity: vi.fn(),
  getCommunicationBalance: vi.fn(),
  getForgottenContacts: vi.fn(),
  getCommunicationTimeline: vi.fn(),
  uploadFile: vi.fn(),
}));

vi.mock("../api", () => api);

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  resetDashboardApi(api);
});

it("requests DM and group-chat lists separately", async () => {
  await renderLoadedDashboard();

  await selectDashboardTab("DMs");
  await waitFor(() =>
    expect(api.getChats).toHaveBeenLastCalledWith(
      1,
      50,
      "total_messages",
      "desc",
      "dm",
    ),
  );

  await selectDashboardTab("Chats");
  await waitFor(() =>
    expect(api.getChats).toHaveBeenLastCalledWith(
      1,
      50,
      "total_messages",
      "desc",
      "group",
    ),
  );
});

describe("dashboard", () => {
  it("supports keyboard tab navigation and keeps inactive sections hidden", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();

    const overviewTab = screen.getByRole("tab", { name: "Overview" });
    await user.click(overviewTab);
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: "DMs" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(window.location.hash).toBe("#dms");
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: "Chats" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(window.location.hash).toBe("#chats");
    await user.keyboard("{ArrowRight}");

    expect(
      screen.getByRole("tab", { name: "Conversation insights" }),
    ).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(window.location.hash).toBe("#conversation-insights");
    expect(
      screen.getByRole("tabpanel", { name: "Conversation insights" }),
    ).not.toHaveAttribute(
      "hidden",
    );
    expect(document.getElementById("overview-panel")).toHaveAttribute("hidden");
  });

  it("loads private Forgotten and group Interactions scopes separately", async () => {
    api.getForgottenContacts.mockImplementation(
      async (_page, _pageSize, _sortBy, _sortDirection, scope) =>
        scope === "group"
          ? {
              ...forgotten,
              summary: { ...forgotten.summary, eligible_contacts: 1 },
              pagination: { ...forgotten.pagination, total: 1 },
              contacts: [
                {
                  ...forgotten.contacts[0],
                  display_name: "Group participant",
                  interaction_chat_count: 4,
                },
              ],
            }
          : forgotten,
    );
    await renderLoadedDashboard();

    await selectDashboardTab("Interactions");
    const interactions = await screen.findByRole("region", {
      name: "Group interactions",
    });
    expect(api.getForgottenContacts).toHaveBeenLastCalledWith(
      1,
      50,
      "ranking_score",
      "desc",
      "group",
    );
    expect(
      within(interactions).getByRole("row", {
        name: /Group participant.*4/,
      }),
    ).toBeInTheDocument();
    expect(
      within(interactions).getByRole("columnheader", { name: "Group chats" }),
    ).toBeInTheDocument();

    await selectDashboardTab("Forgotten");
    const forgottenRegion = screen.getByRole("region", {
      name: "Forgotten contacts",
    });
    expect(api.getForgottenContacts).toHaveBeenLastCalledWith(
      1,
      50,
      "ranking_score",
      "desc",
      "private",
    );
    expect(
      within(forgottenRegion).getByRole("row", { name: /Mika/ }),
    ).toBeInTheDocument();
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
    api.getChats.mockResolvedValue(paginated([]));
    api.getContacts.mockResolvedValue(paginated([]));
    render(<App />);

    expect(await screen.findByText("No imported data yet.")).toBeInTheDocument();
    await selectDashboardTab("Chats");
    expect(
      await screen.findByText("Import a messaging export to see chat statistics."),
    ).toBeInTheDocument();
    await selectDashboardTab("Contacts");
    expect(
      await screen.findByText("Import messages to see incoming communication by sender."),
    ).toBeInTheDocument();
    await selectDashboardTab("Forgotten");
    expect(
      await screen.findByRole("heading", { name: "No imported data yet" }),
    ).toBeInTheDocument();
  });

  it("distinguishes empty results from an account with no conversations or incoming senders", async () => {
    api.getOverview.mockResolvedValue({
      ...overview,
      total_chats: 0,
      total_messages: 8,
    });
    api.getChats.mockResolvedValue(paginated([]));
    api.getContacts.mockResolvedValue(paginated([]));
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

  it("filters chats and contacts only after choosing a matching name", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();

    await selectDashboardTab("Chats");
    const chatsRegion = screen.getByRole("region", { name: "Chats" });
    const chatsTable = within(chatsRegion).getByRole("table");
    await user.click(within(chatsRegion).getByRole("button", { name: "Choose a chat" }));
    await user.type(
      within(chatsRegion).getByRole("searchbox", { name: "Choose a chat search" }),
      "  AURORA ",
    );
    expect(rowTitles(chatsTable)).toHaveLength(chats.length);
    await user.click(
      within(
        screen.getByRole("listbox", { name: "Choose a chat options" }),
      ).getByRole("option", { name: /Aurora group/ }),
    );
    expect(within(chatsRegion).getByRole("row", { name: /Aurora group/ })).toBeInTheDocument();
    expect(within(chatsRegion).queryByRole("row", { name: /Zebra group/ })).not.toBeInTheDocument();

    await selectDashboardTab("Contacts");
    const contactsRegion = screen.getByRole("region", { name: "Contacts & senders" });
    const contactsTable = within(contactsRegion).getByRole("table");
    const averyRow = within(contactsTable).getByRole("row", { name: /Avery/ });
    expect(within(averyRow).getAllByRole("cell").map((cell) => cell.textContent))
      .toEqual(["12345", "TG@anton", "8", "4", "12"]);
    const rowCount = within(contactsTable).getAllByRole("row").length;
    await user.click(within(contactsRegion).getByRole("button", { name: "Choose a contact" }));
    await user.type(
      within(contactsRegion).getByRole("searchbox", { name: "Choose a contact search" }),
      "  mORGAN ",
    );
    expect(within(contactsTable).getAllByRole("row")).toHaveLength(rowCount);
    await user.click(
      within(
        screen.getByRole("listbox", { name: "Choose a contact options" }),
      ).getByRole("option", { name: /Morgan/ }),
    );
    expect(within(contactsRegion).getByRole("row", { name: /Morgan/ })).toBeInTheDocument();
    expect(within(contactsRegion).queryByRole("row", { name: /Avery/ })).not.toBeInTheDocument();
  });

  it("pages chat rows while keeping every chat available in the picker", async () => {
    const user = userEvent.setup();
    const options = chats.map((chat) => ({
      value: String(chat.chat_id),
      label: chat.title || "Untitled chat",
      platforms: [chat.platform],
      search_terms: [chat.platform_chat_id, chat.chat_type],
    }));
    api.getChats
      .mockResolvedValueOnce({
        items: [chats[0]],
        pagination: { page: 1, page_size: 1, total: chats.length },
        options,
      })
      .mockResolvedValueOnce({
        items: [chats[1]],
        pagination: { page: 2, page_size: 1, total: chats.length },
        options,
      });

    render(<App />);
    await selectDashboardTab("Chats");
    const region = screen.getByRole("region", { name: "Chats" });
    expect(await within(region).findByRole("row", { name: /Zebra group/ }))
      .toBeInTheDocument();

    await user.click(within(region).getByRole("button", { name: "Choose a chat" }));
    await user.click(
      within(screen.getByRole("listbox", { name: "Choose a chat options" }))
        .getByRole("option", { name: /Aurora group/ }),
    );

    expect(await within(region).findByRole("row", { name: /Aurora group/ }))
      .toBeInTheDocument();
    expect(api.getChats).toHaveBeenLastCalledWith(
      2,
      50,
      "total_messages",
      "desc",
      "group",
    );
  });

  it("shows no matching options without filtering the page while typing", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    await selectDashboardTab("Chats");

    const region = screen.getByRole("region", { name: "Chats" });
    const originalRows = rowTitles(within(region).getByRole("table"));
    await user.click(within(region).getByRole("button", { name: "Choose a chat" }));
    await user.type(
      within(region).getByRole("searchbox", { name: "Choose a chat search" }),
      "missing",
    );
    expect(within(region).getByText("No chats match these filters.")).toBeInTheDocument();
    expect(rowTitles(within(region).getByRole("table"))).toEqual(originalRows);
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
    expect(
      within(contactsRegion).getByRole("navigation", {
        name: "Contacts pagination above table",
      }),
    ).toBeInTheDocument();
    expect(
      within(contactsRegion).getByRole("navigation", {
        name: "Contacts pagination below table",
      }),
    ).toBeInTheDocument();
    const sortButton = within(contactsRegion).getByRole("button", {
      name: "Sort by Messages sent, descending",
    });

    expect(rowTitles(contactsTable)).toEqual(["Avery", "Morgan"]);
    await user.click(sortButton);
    expect(rowTitles(contactsTable)).toEqual(["Morgan", "Avery"]);
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
    await user.click(within(region).getByRole("button", {
      name: "Choose a forgotten contact",
    }));
    await user.click(
      within(
        screen.getByRole("listbox", {
          name: "Choose a forgotten contact options",
        }),
      ).getByRole("option", { name: /Zoe/ }),
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
    await user.click(within(region).getByRole("button", {
      name: "Choose a forgotten contact",
    }));
    await user.type(
      within(region).getByRole("searchbox", {
        name: "Choose a forgotten contact search",
      }),
      "nobody",
    );
    expect(
      within(region).getByText("No contacts match these filters."),
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
});
