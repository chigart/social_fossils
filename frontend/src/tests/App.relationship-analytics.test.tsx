import {
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { paginated, resetDashboardApi } from "./dashboardTestHelpers";
import {
  chatInsights,
  chats,
  contacts,
} from "./App.testFixtures";
import {
  renderLoadedDashboard,
  selectDashboardTab,
} from "./App.testUtils";

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

describe("dashboard", () => {
  it("shows the dashboard content, aggregate metrics, and sender link states", async () => {
    await renderLoadedDashboard();

    expect(
      screen.getByRole("heading", { name: "Your communication, in context." }),
    ).toBeInTheDocument();
    expect(screen.getByText("Combined account data")).toBeInTheDocument();
    expect(
      screen.queryByText(/All imported Telegram exports are included/),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Dashboard sections" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(10);
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      screen.getByRole("tab", { name: "Conversation insights" }),
    ).toHaveAttribute(
      "aria-controls",
      "conversation-insights-panel",
    );
    expect(screen.getByRole("tab", { name: "Import" })).toHaveAttribute(
      "aria-controls",
      "uploads-panel",
    );
    expect(
      screen.queryByRole("tab", { name: /^Insights$/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("tab", { name: /^Timeline$/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("All messages")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Overview" })).getByText(
        "Ordinary messages",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Overview" })).queryByText(
        "Service events",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Overview" })).getByRole(
        "columnheader",
        { name: "Total contacts" },
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
        /TG@anton/,
      ),
    ).toHaveLength(chats.length);

    await selectDashboardTab("Contacts");
    const contactsRegion = screen.getByRole("region", {
      name: "Contacts & senders",
    });
    expect(
      within(contactsRegion).getByRole("columnheader", { name: "Accounts" }),
    ).toBeInTheDocument();
    expect(
      within(contactsRegion).getByRole("columnheader", { name: "User ID" }),
    ).toBeInTheDocument();
    expect(
      within(contactsRegion).queryByRole("columnheader", {
        name: "Link status",
      }),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Contacts & senders" }))
        .queryByRole("columnheader", { name: "Service events" }),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Contacts & senders" })).getByRole(
        "row",
        { name: /Avery.*TG@anton/ },
      ),
    ).toBeInTheDocument();
    expect(
      within(contactsRegion).getByRole("row", { name: /Avery/ }),
    ).toHaveTextContent("12345");
    expect(
      within(contactsRegion).queryByText(/Unknown sender|Unidentified contact/),
    ).not.toBeInTheDocument();
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

  it("shows one combined contact row for explicitly linked platform identities", async () => {
    const user = userEvent.setup();
    api.getContacts.mockResolvedValue(paginated([
      {
        ...contacts[0],
        platforms: ["instagram", "telegram"],
        identity_group_id: 18,
        source_account_ids: [1, 2],
        source_account_labels: ["@instagram-account", "@telegram-account"],
        source_accounts: [
          { platform: "instagram", label: "@instagram-account" },
          { platform: "telegram", label: "@telegram-account" },
        ],
        source_contact_ids: [1, 2],
        platform_user_ids: ["instagram-peer", "telegram-peer"],
        display_name: "Shared person",
        total_messages_sent: 17,
        personal_chat_messages_sent: 10,
        group_chat_messages_sent: 7,
        ordinary_messages_sent: 15,
      },
    ]));

    await renderLoadedDashboard();
    await selectDashboardTab("Contacts");

    const contactsRegion = screen.getByRole("region", {
      name: "Contacts & senders",
    });
    const contactPicker = within(contactsRegion).getByRole("button", {
      name: "Choose a contact",
    });
    await user.click(contactPicker);
    const contactOptions = screen.getByRole("listbox", {
      name: "Choose a contact options",
    });
    const sharedPersonOption = within(contactOptions).getByRole("option", {
      name: /IG: Shared person.*TG: Shared person/,
    });
    expect(
      sharedPersonOption.querySelectorAll(
        ".bg-platform-instagram-background, .bg-platform-telegram-background",
      ),
    ).toHaveLength(2);
    await user.click(sharedPersonOption);
    expect(contactPicker).toHaveTextContent("IG: Shared person");
    expect(contactPicker).toHaveTextContent("TG: Shared person");
    expect(
      within(contactsRegion).getAllByRole("row", { name: /Shared person/ }),
    ).toHaveLength(1);
    expect(
      within(contactsRegion).getByRole("row", { name: /Shared person/ }),
    ).toHaveTextContent("17");
    const sharedPersonRow = within(contactsRegion).getByRole("row", {
      name: /Shared person/,
    });
    expect(within(sharedPersonRow).getByText("IG@instagram-account"))
      .toBeInTheDocument();
    expect(within(sharedPersonRow).getByText("TG@telegram-account"))
      .toBeInTheDocument();
    const contactAccountBadges = within(contactsRegion)
      .getByRole("row", { name: /Shared person/ })
      .querySelectorAll(".bg-platform-instagram-background, .bg-platform-telegram-background");
    expect(contactAccountBadges).toHaveLength(2);
    expect(
      within(contactsRegion).getByText(
        /Explicitly linked identities are combined across messaging accounts/,
      ),
    ).toBeInTheDocument();
  });

  it("shows only conversation handoffs that occurred at least three times", async () => {
    api.getChatInsights.mockResolvedValue({
      chats: [
        {
          ...chatInsights.chats[0],
          conversation_activity: {
            ...chatInsights.chats[0].conversation_activity,
            attributed_handoff_count: 4,
            handoffs: [
              {
                ...chatInsights.chats[0].conversation_activity.handoffs[0],
                previous_closer_name: "Rare closer",
                next_opener_name: "Rare opener",
                count: 1,
              },
              {
                ...chatInsights.chats[0].conversation_activity.handoffs[0],
                previous_closer_name: "Frequent closer",
                next_opener_name: "Frequent opener",
                count: 3,
              },
            ],
          },
        },
      ],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Conversation insights");

    expect(
      screen.getByRole("heading", { name: "Who reopens after a pause" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Conversation openers" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Conversation closers" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Frequent closer → Frequent opener")).toBeInTheDocument();
    expect(screen.getByText("3 times")).toBeInTheDocument();
    expect(
      screen.queryByText("Rare closer → Rare opener"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("1 times")).not.toBeInTheDocument();
    const panelsGrid = screen
      .getByRole("heading", { name: "Conversation openers" })
      .closest("div.grid");
    expect(panelsGrid).toHaveClass("grid-cols-2");
    const leftColumn = panelsGrid?.children[0];
    const rightColumn = panelsGrid?.children[1];
    expect(leftColumn).toHaveClass("flex-col");
    expect(leftColumn?.children[0]).toContainElement(
      screen.getByRole("heading", { name: "Conversation openers" }),
    );
    expect(leftColumn?.children[1]).toContainElement(
      screen.getByRole("heading", { name: "Conversation closers" }),
    );
    expect(rightColumn).toContainElement(
      screen.getByRole("heading", { name: "Who reopens after a pause" }),
    );
    expect(screen.getByText("Conversation flow")).toBeInTheDocument();
  });

  it("shows only conversation openers and closers that occurred at least three times", async () => {
    api.getChatInsights.mockResolvedValue({
      chats: [
        {
          ...chatInsights.chats[0],
          conversation_activity: {
            ...chatInsights.chats[0].conversation_activity,
            opening_senders: [
              {
                ...chatInsights.chats[0].conversation_activity.opening_senders[0],
                display_name: "Frequent opener",
                count: 3,
              },
              {
                ...chatInsights.chats[0].conversation_activity.opening_senders[1],
                display_name: "Rare opener",
                count: 2,
              },
            ],
            closing_senders: [
              {
                ...chatInsights.chats[0].conversation_activity.closing_senders[0],
                display_name: "Frequent closer",
                count: 4,
              },
              {
                ...chatInsights.chats[0].conversation_activity.closing_senders[1],
                display_name: "Rare closer",
                count: 1,
              },
            ],
          },
        },
      ],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Conversation insights");

    expect(screen.getByText("Frequent opener")).toBeInTheDocument();
    expect(screen.getByText("Frequent closer")).toBeInTheDocument();
    expect(screen.queryByText("Rare opener")).not.toBeInTheDocument();
    expect(screen.queryByText("Rare closer")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Conversation openers" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Conversation closers" }),
    ).toBeInTheDocument();
  });
});
