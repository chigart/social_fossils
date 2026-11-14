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
  const dmsRegion = screen.getByRole("region", { name: "DMs" });
  const dmsTable = within(dmsRegion).getByRole("table");
  expect(within(dmsTable).queryByRole("columnheader", { name: "Type" }))
    .not.toBeInTheDocument();
  expect(within(dmsTable).getAllByRole("columnheader").map((header) => header.textContent?.trim()))
    .toEqual(["Chat title", "Account", "Text volume", "Messages ↓", "First message", "Latest message", "Average time to reply"]);
  expect(within(dmsTable).getByRole("row", { name: /Zebra group/ }))
    .toHaveTextContent("15 min");
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
      screen.getByRole("tab", { name: "Insights" }),
    ).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(window.location.hash).toBe("#conversation-insights");
    expect(
      screen.getByRole("tabpanel", { name: "Insights" }),
    ).not.toHaveAttribute(
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
    expect(within(chatsTable).queryByRole("columnheader", { name: "Type" }))
      .not.toBeInTheDocument();
    expect(within(chatsTable).getAllByRole("columnheader").map((header) => header.textContent?.trim()))
      .toEqual(["Chat title", "Account", "Text volume", "Messages ↓", "Senders", "First message", "Latest message"]);
    expect(within(chatsTable).getAllByRole("cell").some((cell) => cell.classList.contains("text-right")))
      .toBe(false);
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
    expect(within(contactsTable).queryByRole("columnheader", { name: "Messages sent" }))
      .not.toBeInTheDocument();
    const averyRow = within(contactsTable).getByRole("row", { name: /Avery/ });
    expect(within(averyRow).getAllByRole("cell").map((cell) => cell.textContent))
      .toEqual(["12345", "TG@anton", "8", "4"]);
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

  it("filters chat pages by platform and keeps the platform when clearing the name", async () => {
    const user = userEvent.setup();
    const instagramChat = {
      ...chats[0],
      chat_id: 99,
      platform: "instagram",
      title: "Instagram group",
    };
    api.getChats.mockResolvedValue({
      items: [chats[0], instagramChat],
      pagination: { page: 1, page_size: 50, total: 60 },
      options: [
        {
          value: String(chats[0].chat_id),
          label: chats[0].title ?? "Untitled chat",
          platforms: ["telegram"],
          search_terms: [chats[0].platform_chat_id],
        },
        {
          value: String(instagramChat.chat_id),
          label: instagramChat.title ?? "Untitled chat",
          platforms: ["instagram"],
          search_terms: [instagramChat.platform_chat_id],
        },
      ],
    });

    await renderLoadedDashboard();
    await selectDashboardTab("Chats");
    const region = screen.getByRole("region", { name: "Chats" });
    await screen.findByRole("row", { name: /Instagram group/ });

    await user.selectOptions(
      within(region).getByRole("combobox", {
        name: "Filter chats by platform",
      }),
      "telegram",
    );

    expect(api.getChats).toHaveBeenLastCalledWith(
      1,
      50,
      "total_messages",
      "desc",
      "group",
      "telegram",
    );
    expect(within(region).getByRole("row", { name: /Zebra group/ }))
      .toBeInTheDocument();
    expect(within(region).queryByRole("row", { name: /Instagram group/ }))
      .not.toBeInTheDocument();
    expect(within(region).getAllByText("Page 1 of 2 · 60 items"))
      .toHaveLength(2);
    expect(within(region).getAllByRole("button", { name: "Go to page 2" }))
      .toHaveLength(2);

    await user.click(within(region).getByRole("button", { name: "Choose a chat" }));
    await user.click(
      within(screen.getByRole("listbox", { name: "Choose a chat options" }))
        .getByRole("option", { name: /Zebra group/ }),
    );
    expect(within(region).getAllByText("Page 1 of 1 · 1 items"))
      .toHaveLength(2);
    await user.click(within(region).getByRole("button", { name: "Choose a chat" }));
    await user.click(within(region).getByRole("button", { name: "Clear" }));

    expect(
      within(region).getByRole("combobox", {
        name: "Filter chats by platform",
      }),
    ).toHaveValue("telegram");
    expect(within(region).getByRole("button", { name: "Choose a chat" }))
      .toBeInTheDocument();
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

    expect(
      within(chatsTable).queryByRole("columnheader", { name: "Ordinary" }),
    ).not.toBeInTheDocument();
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

  it("sorts chats by senders and message dates, and DMs omit senders", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    await selectDashboardTab("Chats");
    const chatsRegion = screen.getByRole("region", { name: "Chats" });
    const chatsTable = within(chatsRegion).getByRole("table");

    await user.click(
      within(chatsRegion).getByRole("button", { name: "Sort by Senders" }),
    );
    expect(rowTitles(chatsTable)).toEqual([
      "Untitled chat",
      "Zebra group",
      "Aurora group",
    ]);
    expect(api.getChats).toHaveBeenLastCalledWith(
      1,
      50,
      "distinct_identified_senders",
      "asc",
      "group",
    );

    await user.click(
      within(chatsRegion).getByRole("button", { name: "Sort by First message" }),
    );
    expect(rowTitles(chatsTable)).toEqual([
      "Zebra group",
      "Aurora group",
      "Untitled chat",
    ]);
    expect(api.getChats).toHaveBeenLastCalledWith(
      1,
      50,
      "earliest_message_timestamp",
      "asc",
      "group",
    );

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
    const dmsRegion = screen.getByRole("region", { name: "DMs" });
    const dmsTable = within(dmsRegion).getByRole("table");
    expect(
      within(dmsTable).queryByRole("columnheader", { name: "Senders" }),
    ).not.toBeInTheDocument();
    expect(
      within(dmsRegion).getByRole("button", { name: "Sort by Latest message" }),
    ).toBeInTheDocument();
    const textVolumeSort = within(dmsRegion).getByRole("button", {
      name: "Sort by Text volume",
    });
    expect(textVolumeSort).toBeInTheDocument();
    await user.click(textVolumeSort);
    expect(api.getChats).toHaveBeenLastCalledWith(
      1,
      50,
      "text_length",
      "asc",
      "dm",
    );
    await user.click(
      within(dmsRegion).getByRole("button", {
        name: "Sort by Average time to reply",
      }),
    );
    expect(api.getChats).toHaveBeenLastCalledWith(
      1,
      50,
      "average_response_seconds",
      "asc",
      "dm",
    );
  });

  it("toggles group-message sorting between ascending and descending", async () => {
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
      name: "Sort by Group messages",
    });

    expect(rowTitles(contactsTable)).toEqual(["Avery", "Morgan"]);
    await user.click(sortButton);
    expect(rowTitles(contactsTable)).toEqual(["Avery", "Morgan"]);
    expect(sortButton).toHaveAttribute(
      "aria-label",
      "Sort by Group messages, ascending",
    );
    await user.click(sortButton);
    expect(rowTitles(contactsTable)).toEqual(["Morgan", "Avery"]);
    expect(sortButton).toHaveAttribute(
      "aria-label",
      "Sort by Group messages, descending",
    );
  });

  it("sorts contacts by DM and group message counts", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    await selectDashboardTab("Contacts");
    const contactsRegion = screen.getByRole("region", {
      name: "Contacts & senders",
    });
    const contactsTable = within(contactsRegion).getByRole("table");

    await user.click(
      within(contactsRegion).getByRole("button", {
        name: "Sort by Group messages",
      }),
    );
    expect(rowTitles(contactsTable)).toEqual(["Avery", "Morgan"]);
    expect(api.getContacts).toHaveBeenLastCalledWith(
      1,
      50,
      "group_chat_messages_sent",
      "asc",
    );

    await user.click(
      within(contactsRegion).getByRole("button", {
        name: "Sort by DM messages",
      }),
    );
    expect(rowTitles(contactsTable)).toEqual(["Morgan", "Avery"]);
    expect(api.getContacts).toHaveBeenLastCalledWith(
      1,
      50,
      "personal_chat_messages_sent",
      "asc",
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

});
