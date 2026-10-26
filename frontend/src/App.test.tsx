import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  balance,
  chatInsights,
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

vi.mock("./api", () => api);

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  Object.values(api).forEach((mock) => mock.mockReset());
  api.getOverview.mockResolvedValue(overview);
  api.getChatInsights.mockResolvedValue(chatInsights);
  api.getChats.mockResolvedValue(chats);
  api.getContacts.mockResolvedValue(contacts);
  api.getIdentityLinks.mockResolvedValue({
    identities: [],
    contacts_without_identity: [],
    events: [],
  });
  api.linkPlatformIdentities.mockResolvedValue({
    status: "linked",
    identity_group_id: 1,
  });
  api.unlinkPlatformIdentity.mockResolvedValue({
    status: "unlinked",
    identity_group_id: null,
  });
  api.getCommunicationBalance.mockResolvedValue(balance);
  api.getForgottenContacts.mockResolvedValue(forgotten);
  api.getCommunicationTimeline.mockResolvedValue(timeline);
});

describe("dashboard", () => {
  it("opens the multi-file uploader from the Import tab", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    await selectDashboardTab("Import");

    expect(
      screen.getByRole("heading", { name: "Import files" }),
    ).toBeInTheDocument();
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "telegram",
    );
    expect(
      screen.getByLabelText("Choose Telegram JSON files"),
    ).toHaveAttribute("multiple");
  });

  it("links and unlinks platform identities explicitly", async () => {
    const user = userEvent.setup();
    const firstIdentity = {
      identity_id: 1,
      platform: "telegram",
      platform_user_id: "telegram-user-1",
      identity_group_id: null,
      contacts: [],
    };
    const secondIdentity = {
      identity_id: 2,
      platform: "instagram",
      platform_user_id: "instagram-user-1",
      identity_group_id: null,
      contacts: [],
    };
    const initial = {
      identities: [firstIdentity, secondIdentity],
      contacts_without_identity: [
        {
          contact_id: 7,
          account_id: 8,
          account_label: "Synthetic Instagram account",
          platform: "instagram",
          display_name: "Unidentified message participant",
          username: null,
        },
      ],
      events: [],
    };
    const linked = {
      ...initial,
      identities: [
        { ...firstIdentity, identity_group_id: 3 },
        { ...secondIdentity, identity_group_id: 3 },
      ],
      events: [
        {
          id: 1,
          group_id: 3,
          identity_id: 1,
          peer_identity_id: 2,
          action: "linked" as const,
          source: "dashboard",
          occurred_at: "2026-10-24T08:00:00Z",
        },
      ],
    };
    const unlinked = {
      ...initial,
      events: [
        ...linked.events,
        {
          id: 2,
          group_id: 3,
          identity_id: 1,
          peer_identity_id: 2,
          action: "unlinked" as const,
          source: "dashboard",
          occurred_at: "2026-10-24T08:01:00Z",
        },
      ],
    };
    api.getIdentityLinks
      .mockResolvedValueOnce(initial)
      .mockResolvedValueOnce(linked)
      .mockResolvedValueOnce(unlinked);
    render(<App />);
    await selectDashboardTab("Identity links");

    const identityPanel = screen.getByRole("region", {
      name: "Identity links",
    });
    await user.click(
      within(identityPanel).getByRole("button", {
        name: "First platform identity",
      }),
    );
    expect(
      within(identityPanel).getByRole("listbox", {
        name: "First platform identity options",
      }),
    ).toBeVisible();
    await user.click(
      within(identityPanel).getByRole("option", {
        name: /TG: telegram-user-1/,
      }),
    );
    await user.click(
      within(identityPanel).getByRole("button", {
        name: "Second platform identity",
      }),
    );
    await user.click(
      within(identityPanel).getByRole("option", {
        name: /IG: instagram-user-1/,
      }),
    );
    const linkButton = within(identityPanel).getByRole("button", {
      name: "Link identities",
    });
    expect(linkButton).toHaveClass(
      "bg-surface-brand",
      "text-brand-strong",
      "hover:brightness-95",
    );
    await user.click(linkButton);

    expect(api.linkPlatformIdentities).toHaveBeenCalledWith(1, 2);
    expect(
      await within(identityPanel).findByText("Linked person group 3"),
    ).toBeInTheDocument();
    expect(
      within(identityPanel).getAllByText("TG:", { exact: false }),
    ).toHaveLength(2);
    expect(
      within(identityPanel).getAllByText("IG:", { exact: false }),
    ).toHaveLength(2);
    expect(
      within(identityPanel).queryByText("Unidentified message participant"),
    ).not.toBeInTheDocument();
    expect(
      within(identityPanel).queryByRole("heading", {
        name: "Contacts without a platform identity",
      }),
    ).not.toBeInTheDocument();

    const linkedGroup = within(identityPanel).getByText(
      "Linked person group 3",
    ).parentElement;
    expect(linkedGroup?.querySelector("ul")).toHaveClass(
      "flex",
      "flex-wrap",
      "items-center",
    );
    const unlinkButton = within(identityPanel).getByRole("button", {
      name: "Unlink TG: telegram-user-1",
    });
    expect(unlinkButton).toHaveClass(
      "bg-border-warning",
      "text-brand-strong",
      "hover:brightness-95",
    );
    expect(
      [...unlinkButton.classList].filter((className) => !className.startsWith("bg-")),
    ).toEqual(
      [...linkButton.classList].filter((className) => !className.startsWith("bg-")),
    );

    await user.click(
      within(identityPanel).getByRole("button", {
        name: "Unlink TG: telegram-user-1",
      }),
    );
    expect(api.unlinkPlatformIdentity).toHaveBeenCalledWith(1);
    expect(
      await within(identityPanel).findByRole("heading", {
        name: "No cross-platform links yet",
      }),
    ).toBeInTheDocument();
  });

  it("shows every account in a multi-platform identity group", async () => {
    const identities = [
      ["telegram", "telegram-1"],
      ["telegram", "telegram-2"],
      ["instagram", "instagram-1"],
      ["instagram", "instagram-2"],
      ["discord", "discord-1"],
    ].map(([platform, platformUserId], index) => ({
      identity_id: index + 1,
      platform,
      platform_user_id: platformUserId,
      identity_group_id: 7,
      contacts: [],
    }));
    api.getIdentityLinks.mockResolvedValueOnce({
      identities,
      contacts_without_identity: [],
      events: [],
    });

    render(<App />);
    await selectDashboardTab("Identity links");

    const linkedGroup = screen.getByText("Linked person group 7").parentElement;
    expect(linkedGroup?.querySelectorAll("li")).toHaveLength(5);
    expect(
      within(linkedGroup as HTMLElement).getAllByRole("button", {
        name: /^Unlink/,
      }),
    ).toHaveLength(5);
  });

  it("filters identity picker options by search and platform", async () => {
    const user = userEvent.setup();
    const identities = [
      {
        identity_id: 1,
        platform: "telegram",
        platform_user_id: "tg-user-1",
        identity_group_id: null,
        contacts: [{
          contact_id: 1,
          account_id: 1,
          account_label: "Telegram",
          platform: "telegram",
          display_name: "Alex Example",
          username: "alex_tg",
        }],
      },
      {
        identity_id: 2,
        platform: "instagram",
        platform_user_id: "ig-user-2",
        identity_group_id: null,
        contacts: [{
          contact_id: 2,
          account_id: 2,
          account_label: "Instagram",
          platform: "instagram",
          display_name: "Alex Example",
          username: "alex_ig",
        }],
      },
      {
        identity_id: 3,
        platform: "instagram",
        platform_user_id: "ig-user-3",
        identity_group_id: null,
        contacts: [{
          contact_id: 3,
          account_id: 2,
          account_label: "Instagram",
          platform: "instagram",
          display_name: "Blair Example",
          username: "blair",
        }],
      },
    ];
    api.getIdentityLinks.mockResolvedValueOnce({
      identities,
      contacts_without_identity: [],
      events: [],
    });
    render(<App />);
    await selectDashboardTab("Identity links");

    await user.click(screen.getByRole("button", {
      name: "First platform identity",
    }));
    const search = screen.getByRole("searchbox", {
      name: "First platform identity search",
    });
    await user.type(search, "Blair");
    let options = screen.getByRole("listbox", {
      name: "First platform identity options",
    });
    expect(within(options).getAllByRole("option")).toHaveLength(1);
    expect(within(options).getByRole("option", { name: /IG: Blair Example/ }))
      .toBeInTheDocument();

    await user.clear(search);
    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "First platform identity platform filter",
      }),
      "telegram",
    );
    options = screen.getByRole("listbox", {
      name: "First platform identity options",
    });
    expect(within(options).getAllByRole("option")).toHaveLength(1);
    expect(within(options).getByRole("option", { name: /TG: Alex Example/ }))
      .toBeInTheDocument();
  });

  it("orders suggestions by match rank, then name length", async () => {
    const user = userEvent.setup();
    const pairs = [
      ["Mira Moon", "Mira Moon"],
      ["Grace Moonrise", "Grace Moonrise"],
      ["Alex Star", "Alex Stab"],
      ["Alexandria Starling", "Alexandria Starlinh"],
      ["Casey Earth", "Casey Ezzth"],
      ["Quentin Earth", "Quentin Ezzth"],
      ["Rowan Vale", "Rowan Hart"],
      ["Theodore Smith", "Theodore Jones"],
    ];
    const identities = pairs.flatMap(([telegramName, instagramName], index) => {
      const telegramId = index * 2 + 1;
      const instagramId = telegramId + 1;
      return [
        {
          identity_id: telegramId,
          platform: "telegram",
          platform_user_id: `telegram-${telegramId}`,
          identity_group_id: null,
          contacts: [{
            contact_id: telegramId,
            account_id: 1,
            account_label: "Telegram",
            platform: "telegram",
            display_name: telegramName,
            username: null,
          }],
        },
        {
          identity_id: instagramId,
          platform: "instagram",
          platform_user_id: `instagram-${instagramId}`,
          identity_group_id: null,
          contacts: [{
            contact_id: instagramId,
            account_id: 2,
            account_label: "Instagram",
            platform: "instagram",
            display_name: instagramName,
            username: null,
          }],
        },
      ];
    });
    api.getIdentityLinks.mockResolvedValueOnce({
      identities,
      contacts_without_identity: [],
      events: [],
    });
    render(<App />);
    await selectDashboardTab("Identity links");

    const suggestions = screen.getByRole("list", {
      name: "Suggested identity links",
    });
    expect(Array.from(suggestions.querySelectorAll("strong"), (item) =>
      item.textContent?.trim().replace(/\s+/g, " ")
    )).toEqual([
      "Full Name match:",
      "Full Name match:",
      "1-symbol Full Name difference:",
      "1-symbol Full Name difference:",
      "2-symbol Full Name difference:",
      "2-symbol Full Name difference:",
      "First or last name match:",
      "First or last name match:",
    ]);
    const suggestionItems = within(suggestions).getAllByRole("listitem");
    expect(suggestionItems[0]).toHaveTextContent("Grace Moonrise");
    expect(suggestionItems[1]).toHaveTextContent("Mira Moon");
    expect(suggestionItems[2]).toHaveTextContent("Alexandria Starling");
    expect(suggestionItems[3]).toHaveTextContent("Alex Star");
    expect(suggestionItems[4]).toHaveTextContent("Quentin Earth");
    expect(suggestionItems[5]).toHaveTextContent("Casey Earth");
    expect(suggestionItems[6]).toHaveTextContent("Theodore Smith");
    expect(suggestionItems[7]).toHaveTextContent("Rowan Vale");
    const suggestionLinkButton = within(suggestions).getAllByRole("button", {
      name: "Link identities",
    })[0];
    expect(suggestionLinkButton).toHaveClass(
      "bg-surface-brand",
      "text-brand-strong",
      "hover:brightness-95",
    );
    await user.click(
      within(suggestions).getAllByRole("button", {
        name: "Link identities",
      })[0],
    );
    expect(api.linkPlatformIdentities).toHaveBeenCalledWith(3, 4);
  });

  it("keeps current links and suggestions in vertically scrollable lists", async () => {
    const names = [
      "Ada Moon",
      "Bert Lake",
      "Cora Stone",
      "Dale Reed",
      "Evan Park",
      "Faye Hill",
      "Glen Frost",
      "Hope Vale",
      "Iris Cloud",
      "Jude Field",
      "Kira Brook",
      "Liam Shore",
    ];
    const suggestedIdentities = names.flatMap((name, index) => {
      const id = index * 2 + 1;
      return [
        {
          identity_id: id,
          platform: "telegram",
          platform_user_id: `telegram-${id}`,
          identity_group_id: null,
          contacts: [{
            contact_id: id,
            account_id: 1,
            account_label: "Telegram",
            platform: "telegram",
            display_name: name,
            username: null,
          }],
        },
        {
          identity_id: id + 1,
          platform: "instagram",
          platform_user_id: `instagram-${id + 1}`,
          identity_group_id: null,
          contacts: [{
            contact_id: id + 1,
            account_id: 2,
            account_label: "Instagram",
            platform: "instagram",
            display_name: name,
            username: null,
          }],
        },
      ];
    });
    const currentIdentities = Array.from({ length: 11 }, (_, index) => {
      const id = 100 + index * 2;
      const groupId = 200 + index;
      return [
        {
          identity_id: id,
          platform: "telegram",
          platform_user_id: `telegram-${id}`,
          identity_group_id: groupId,
          contacts: [],
        },
        {
          identity_id: id + 1,
          platform: "instagram",
          platform_user_id: `instagram-${id + 1}`,
          identity_group_id: groupId,
          contacts: [],
        },
      ];
    }).flat();
    api.getIdentityLinks.mockResolvedValueOnce({
      identities: [...suggestedIdentities, ...currentIdentities],
      contacts_without_identity: [],
      events: [],
    });
    render(<App />);
    await selectDashboardTab("Identity links");

    const currentLinks = screen.getByLabelText("Current identity links");
    expect(currentLinks).toHaveClass("max-h-[600px]", "overflow-y-auto");
    expect(within(currentLinks).getAllByText(/^Linked person group/)).toHaveLength(11);

    const suggestions = screen.getByRole("list", {
      name: "Suggested identity links",
    });
    expect(suggestions).toHaveClass("max-h-[600px]", "overflow-y-auto");
    expect(within(suggestions).getAllByRole("button", {
      name: "Link identities",
    })).toHaveLength(12);
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
        source_accounts: [
          { platform: "telegram", label: "@anton" },
          { platform: "telegram", label: "Anton Malkov" },
        ],
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
        name: /First account chat.*TG@anton/,
      }),
    ).toBeInTheDocument();
    expect(
      within(chatRegion).getByRole("row", {
        name: /Second account chat.*TG Anton Malkov/,
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
    expect(combinedContactRows[0]).toHaveTextContent(
      "TG@anton, TG Anton Malkov",
    );
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
    expect(screen.getByText("Combined account data")).toBeInTheDocument();
    expect(
      screen.queryByText(/All imported Telegram exports are included/),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Dashboard sections" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(8);
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
    api.getContacts.mockResolvedValue([
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
        ordinary_messages_sent: 15,
      },
    ]);

    await renderLoadedDashboard();
    await selectDashboardTab("Contacts");

    const contactsRegion = screen.getByRole("region", {
      name: "Contacts & senders",
    });
    expect(
      within(contactsRegion).getAllByRole("row", { name: /Shared person/ }),
    ).toHaveLength(1);
    expect(
      within(contactsRegion).getByRole("row", { name: /Shared person/ }),
    ).toHaveTextContent("17");
    expect(
      within(contactsRegion).getByRole("row", { name: /Shared person/ }),
    ).toHaveTextContent("IG@instagram-account, TG@telegram-account");
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

  it("shows per-chat word, emoji, and observed reaction insights", async () => {
    const user = userEvent.setup();
    const chatWithSingleUseItems = {
      ...chatInsights.chats[0],
      popular_words: [
        ...chatInsights.chats[0].popular_words,
        { word: "single-chat-word", count: 1 },
      ],
      popular_emojis: [
        ...chatInsights.chats[0].popular_emojis,
        { emoji: "🫥", count: 1 },
      ],
      senders: chatInsights.chats[0].senders.map((sender, index) =>
        index === 0
          ? {
              ...sender,
              popular_words: [
                ...sender.popular_words,
                { word: "single-sender-word", count: 1 },
              ],
              popular_emojis: [
                ...sender.popular_emojis,
                { emoji: "🫡", count: 1 },
              ],
            }
          : sender,
      ),
    };
    api.getChatInsights.mockResolvedValue({
      chats: [
        chatWithSingleUseItems,
        {
          ...chatInsights.chats[0],
          chat_id: 11,
          title: "One-to-one chat",
          chat_type: "personal_chat",
          ordinary_message_count: 5,
          text_length: 12,
        },
      ],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Conversation insights");

    expect(
      screen.getByRole("heading", { name: "Chat insights" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("group", { name: "Matching chats" })).getAllByRole(
        "button",
      ),
    ).toHaveLength(2);
    const messageShare = screen.getByRole("region", {
      name: "Share of messages by person",
    });
    expect(within(messageShare).getByRole("img")).toHaveAccessibleName(
      "Share of messages by person: Anton 60.0%, Lena 40.0%",
    );
    expect(messageShare).toHaveTextContent("12 messages · 60.0%");
    expect(messageShare).toHaveTextContent("8 messages · 40.0%");
    const textShare = screen.getByRole("region", {
      name: "Share of text volume by person",
    });
    expect(within(textShare).getByRole("img")).toHaveAccessibleName(
      "Share of text volume by person: Anton 59.1%, Lena 40.9%",
    );
    expect(textShare).toHaveTextContent("260 characters · 59.1%");
    expect(textShare).toHaveTextContent("180 characters · 40.9%");
    const averageMessageLength = screen.getByRole("region", {
      name: "Average message length by person",
    });
    expect(averageMessageLength).toHaveTextContent(
      "Average message length by person (all senders)",
    );
    const averageLengthChart = within(averageMessageLength).getByRole("img", {
      name: "Average message length by person",
    });
    expect(averageLengthChart).toBeInTheDocument();
    expect(averageLengthChart.parentElement).toHaveClass("overflow-x-auto");
    expect(averageLengthChart).toHaveAccessibleDescription(
      /scrolled horizontally/,
    );
    const senderNameLabel = averageLengthChart.querySelector(
      'text[data-sender-name="Anton"]',
    );
    expect(
      Array.from(senderNameLabel?.querySelectorAll("tspan") ?? [])
        .map((line) => line.textContent)
        .join(" "),
    ).toBe("Anton");
    expect(
      within(averageMessageLength).getByRole("list", {
        name: "Average message length details",
      }),
    ).toHaveTextContent(
      "Lena: 22.5 characters per message (180 characters across 8 messages)",
    );
    expect(
      within(averageMessageLength).getByRole("list", {
        name: "Average message length details",
      }),
    ).toHaveTextContent(
      "Anton: 21.7 characters per message (260 characters across 12 messages)",
    );
    expect(screen.getByText("Most popular words")).toBeInTheDocument();
    expect(screen.getByText("Conversation flow")).toBeInTheDocument();
    expect(
      screen.queryByText("Who reopens after a pause"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Anton → Lena")).not.toBeInTheDocument();
    expect(screen.getByText("Message type breakdown")).toBeInTheDocument();
    expect(screen.getByText("Photo")).toBeInTheDocument();
    const messageTypeBreakdown = screen.getByRole("region", {
      name: "Message type breakdown",
    });
    expect(
      within(messageTypeBreakdown).getByRole("listitem", {
        name: "Anton, 2 messages, 66.7%",
      }),
    ).toBeInTheDocument();
    expect(
      within(messageTypeBreakdown).getByRole("img", {
        name: "Photo sender share: Anton 66.7%, Lena 33.3%",
      }),
    ).toBeInTheDocument();
    expect(
      within(messageTypeBreakdown).getByRole("img", {
        name: "Video sender share: Lena 100.0%",
      }),
    ).toBeInTheDocument();
    expect(messageTypeBreakdown).toHaveTextContent(
      "Each category has its own pie chart, using its top 5 senders normalized to 100%",
    );
    const messageTypeCharts = within(messageTypeBreakdown).getAllByRole("article");
    expect(messageTypeCharts).toHaveLength(2);
    expect(messageTypeCharts[0].parentElement).toHaveClass("grid-cols-3");
    expect(
      within(messageTypeBreakdown).queryByRole("listitem", {
        name: "Text, 20 messages, 20 with text",
      }),
    ).not.toBeInTheDocument();
    expect(
      within(messageTypeBreakdown).queryByRole("listitem", {
        name: "Unclassified, 2 messages, 0 with text",
      }),
    ).not.toBeInTheDocument();
    expect(
      within(messageTypeBreakdown).getByRole("listitem", {
        name: "Lena, 1 messages, 33.3%",
      }),
    ).toBeInTheDocument();
    expect(
      within(messageTypeBreakdown).queryByRole("listitem", {
        name: "Anton, 20 messages, 100.0%",
      }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("30 min")).toBeInTheDocument();
    expect(screen.getByText("Popular words and emojis by sender")).toBeInTheDocument();
    expect(screen.getByText("Observed reactions by person")).toBeInTheDocument();
    const popularWordChip = screen.getByRole("listitem", {
      name: "hello, 8 uses",
    });
    expect(popularWordChip).toBeInTheDocument();
    expect(popularWordChip.querySelector("span")).toHaveClass(
      "font-semibold",
      "text-ink",
    );
    expect(popularWordChip.querySelectorAll("span")[1]).toHaveClass(
      "text-caption",
      "text-ink-muted",
    );
    expect(
      screen.getByRole("listitem", { name: "❤️, 5 uses" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("listitem", { name: "single-chat-word, 1 uses" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("listitem", { name: "🫥, 1 uses" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("listitem", { name: "single-sender-word, 1 uses" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("listitem", { name: "🫡, 1 uses" }),
    ).not.toBeInTheDocument();
    const senderWordChip = screen.getByRole("listitem", {
      name: "hello, 6 uses",
    });
    expect(senderWordChip.querySelector("span")).toHaveClass(
      "font-semibold",
      "text-ink",
    );
    const senderEmojiChip = screen.getByRole("listitem", {
      name: "❤️, 3 uses",
    });
    expect(senderEmojiChip.querySelector("span")).toHaveClass("text-base");
    expect(senderEmojiChip.querySelectorAll("span")[1]).toHaveClass(
      "text-caption",
      "text-ink-muted",
    );
    expect(screen.getByRole("columnheader", { name: "Top reactions" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Most popular reactions · 17 total",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("listitem", { name: "👍, 11 reactions" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("listitem", {
        name: "👍, 4 observed reactions",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("listitem", {
        name: "❤️, 2 observed reactions",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Lena → Anton")).toBeInTheDocument();
    expect(screen.getByText("50.0%")).toBeInTheDocument();
    expect(
      screen.getByText(/show observed coverage and are lower bounds/i),
    ).toBeInTheDocument();

    await user.click(
      within(screen.getByRole("group", { name: "Matching chats" })).getByRole(
        "button",
        { name: /One-to-one chat/ },
      ),
    );
    expect(
      within(screen.getByRole("region", { name: "Chat insights" }))
        .getByRole("heading", { name: "Ordinary messages" })
        .closest("article"),
    ).toHaveTextContent("5");
  });

  it("limits both sender pie charts to the top ten and groups remaining senders", async () => {
    api.getChatInsights.mockResolvedValue({
      chats: [
        {
          ...chatInsights.chats[0],
          ordinary_message_count: 78,
          text_length: 780,
          senders: Array.from({ length: 12 }, (_, index) => ({
            sender_id: `user-${index + 1}`,
            display_name: `Sender ${index + 1}`,
            message_count: 12 - index,
            text_length: (12 - index) * 10,
            popular_words: [],
            popular_emojis: [],
          })),
        },
      ],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Conversation insights");

    const messageShare = screen.getByRole("region", {
      name: "Share of messages by person",
    });
    const textShare = screen.getByRole("region", {
      name: "Share of text volume by person",
    });
    expect(within(messageShare).getAllByRole("listitem")).toHaveLength(11);
    expect(within(textShare).getAllByRole("listitem")).toHaveLength(11);
    expect(within(messageShare).getByText("Sender 1")).toBeInTheDocument();
    expect(within(messageShare).queryByText("Sender 11")).not.toBeInTheDocument();
    expect(within(messageShare).getByText("Other senders")).toBeInTheDocument();
    expect(messageShare).toHaveTextContent("3 messages · 3.8%");
    expect(within(textShare).getByText("Other senders")).toBeInTheDocument();
    expect(textShare).toHaveTextContent("30 characters · 3.8%");
  });

  it("sorts insight chats by message count and searches their titles", async () => {
    const user = userEvent.setup();
    api.getChatInsights.mockResolvedValue({
      chats: [
        {
          ...chatInsights.chats[0],
          chat_id: 10,
          title: "Medium chat",
          ordinary_message_count: 20,
        },
        {
          ...chatInsights.chats[0],
          chat_id: 11,
          title: "One-to-one chat",
          ordinary_message_count: 5,
        },
        {
          ...chatInsights.chats[0],
          chat_id: 12,
          title: "Most active chat",
          ordinary_message_count: 30,
        },
      ],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Conversation insights");

    const matchingChats = screen.getByRole("group", { name: "Matching chats" });
    const optionLabels = within(matchingChats)
      .getAllByRole("button")
      .map((option) => option.textContent);
    expect(optionLabels[0]).toContain("Most active chat");
    expect(optionLabels[0]).toContain("30 messages");
    expect(optionLabels[1]).toContain("Medium chat");
    expect(optionLabels[2]).toContain("One-to-one chat");

    await user.type(
      screen.getByRole("searchbox", { name: "Search chats by title" }),
      "one-to-one",
    );
    const filteredResults = within(matchingChats).getAllByRole("button");
    expect(filteredResults).toHaveLength(1);
    expect(filteredResults[0]).toHaveTextContent("One-to-one chat");
    expect(filteredResults[0]).toHaveTextContent("5 messages");
    await user.click(filteredResults[0]);

    expect(
      within(screen.getByRole("region", { name: "Chat insights" }))
        .getByRole("heading", { name: "Ordinary messages" })
        .closest("article"),
    ).toHaveTextContent("5");

    const filteredLabels = within(matchingChats)
      .getAllByRole("button")
      .map((option) => option.textContent);
    expect(filteredLabels).toHaveLength(1);
    expect(filteredLabels[0]).toContain("One-to-one chat");
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

  it("maps legacy insight and timeline hashes to the combined destination", async () => {
    window.history.replaceState(null, "", "/#communication-timeline");
    await renderLoadedDashboard();

    expect(
      screen.getByRole("tab", { name: "Conversation insights" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(
      screen.getByRole("tabpanel", { name: "Conversation insights" }),
    ).not.toHaveAttribute("hidden");

    window.history.replaceState(null, "", "/#chat-insights");
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    expect(
      screen.getByRole("tab", { name: "Conversation insights" }),
    ).toHaveAttribute("aria-selected", "true");
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
      await screen.findByText("Import a messaging export to see chat statistics."),
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

  it("uses one chat selection for the timeline and insight details", async () => {
    const user = userEvent.setup();
    api.getChatInsights.mockResolvedValue({
      chats: [
        {
          ...chatInsights.chats[0],
          chat_id: 10,
          title: "Private group",
        },
        {
          ...chatInsights.chats[0],
          chat_id: 11,
          title: "One-to-one chat",
          ordinary_message_count: 5,
        },
      ],
    });
    api.getCommunicationTimeline
      .mockResolvedValueOnce(timeline)
      .mockResolvedValueOnce({
        ...timeline,
        summary: {
          ...timeline.summary,
          chat_id: 11,
          ordinary_message_count: 2,
          owner_message_count: 1,
          contact_message_count: 1,
        },
        months: timeline.months.map((month) => ({
          ...month,
          ordinary_message_count: month.month === "2023-03" ? 2 : 0,
          owner_message_count: month.month === "2023-03" ? 1 : 0,
          contact_message_count: month.month === "2023-03" ? 1 : 0,
          unknown_direction_message_count: 0,
          active_days: month.month === "2023-03" ? 1 : 0,
        })),
      });
    await renderLoadedDashboard();
    await selectDashboardTab("Conversation insights");

    const region = screen.getByRole("region", {
      name: "Communication timeline",
    });
    expect(
      screen.getAllByRole("searchbox", { name: "Search chats by title" }),
    ).toHaveLength(1);
    expect(
      screen.queryByRole("combobox", { name: "Timeline scope" }),
    ).not.toBeInTheDocument();
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
      screen.getByRole("heading", { name: "Active days" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Owner messages" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Contact messages" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Text volume" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Emoji reactions" }),
    ).toBeInTheDocument();
    const orderedHeadings = [
      ...screen.getAllByRole("heading"),
    ].map((heading) => heading.textContent);
    expect(orderedHeadings.indexOf("Communication timeline")).toBeLessThan(
      orderedHeadings.indexOf("Ordinary messages"),
    );
    expect(orderedHeadings.indexOf("Ordinary messages")).toBeLessThan(
      orderedHeadings.indexOf("Share of messages by person (top 10 senders)"),
    );

    await user.click(
      within(screen.getByRole("group", { name: "Matching chats" })).getByRole(
        "button",
        { name: /One-to-one chat/ },
      ),
    );

    expect(api.getCommunicationTimeline).toHaveBeenNthCalledWith(2, undefined, 11);
    expect(
      await within(region).findByRole("img", {
        name: "Monthly ordinary message activity",
      }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Active days"),
    ).toBeInTheDocument();
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
    await selectDashboardTab("Conversation insights");

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
