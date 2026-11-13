import {
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { paginated, resetDashboardApi } from "./dashboardTestHelpers";
import {
  chats,
  contacts,
  overview,
} from "./App.testFixtures";
import {
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

describe("dashboard", () => {
  it("suggests extending and merging linked groups but excludes the owner account", async () => {
    const user = userEvent.setup();
    const identities = [
      {
        identity_id: 1,
        platform: "telegram",
        platform_user_id: "telegram-group-one",
        identity_group_id: 10,
        is_owner: false,
        contacts: [{
          contact_id: 1,
          account_id: 1,
          account_label: "Telegram",
          platform: "telegram",
          display_name: "Jordan Pine",
          username: null,
        }],
      },
      {
        identity_id: 2,
        platform: "instagram",
        platform_user_id: "instagram-group-two",
        identity_group_id: 20,
        is_owner: false,
        contacts: [{
          contact_id: 2,
          account_id: 2,
          account_label: "Instagram",
          platform: "instagram",
          display_name: "Jordan Pine",
          username: null,
        }],
      },
      {
        identity_id: 3,
        platform: "discord",
        platform_user_id: "discord-unlinked",
        identity_group_id: null,
        is_owner: false,
        contacts: [{
          contact_id: 3,
          account_id: 3,
          account_label: "Discord",
          platform: "discord",
          display_name: "Jordan Pine",
          username: null,
        }],
      },
      {
        identity_id: 4,
        platform: "facebook",
        platform_user_id: "owner-facebook-id",
        identity_group_id: null,
        is_owner: true,
        contacts: [{
          contact_id: 4,
          account_id: 4,
          account_label: "Facebook",
          platform: "facebook",
          display_name: "Jordan Pine",
          username: null,
        }],
      },
    ];
    api.getIdentityLinks.mockResolvedValueOnce({
      identities,
      contacts_without_identity: [],
      events: [],
    });
    render(<App />);
    await selectDashboardTab("Links");

    const suggestions = screen.getByRole("list", {
      name: "Suggested identity links",
    });
    expect(within(suggestions).getAllByRole("button", {
      name: "Link identities",
    })).toHaveLength(3);
    expect(suggestions).not.toHaveTextContent("owner-facebook-id");

    await user.click(screen.getByRole("button", {
      name: /First platform identity/,
    }));
    expect(screen.queryByRole("option", {
      name: /owner-facebook-id/,
    })).not.toBeInTheDocument();

    await user.click(within(suggestions).getAllByRole("button", {
      name: "Link identities",
    })[0]);
    expect(api.linkPlatformIdentities).toHaveBeenCalledWith(1, 2);
  });

  it("sorts current identity groups by full name", async () => {
    const groups: Array<[string, number]> = [
      ["Zoe Harbor", 30],
      ["Ada Meadow", 20],
      ["Milo Forest", 10],
    ];
    const identities = groups.flatMap(([name, group], index) => {
      const id = index * 2 + 1;
      return [
        {
          identity_id: id,
          platform: "telegram",
          platform_user_id: `telegram-${id}`,
          identity_group_id: group,
          is_owner: false,
          contacts: [{
            contact_id: id,
            account_id: id,
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
          identity_group_id: group,
          is_owner: false,
          contacts: [],
        },
      ];
    });
    api.getIdentityLinks.mockResolvedValueOnce({
      identities,
      contacts_without_identity: [],
      events: [],
    });
    render(<App />);
    await selectDashboardTab("Links");

    const currentLinks = screen.getByLabelText("Current identity links");
    const renderedLinks = currentLinks.textContent ?? "";
    expect(renderedLinks.indexOf("Ada Meadow")).toBeLessThan(
      renderedLinks.indexOf("Milo Forest"),
    );
    expect(renderedLinks.indexOf("Milo Forest")).toBeLessThan(
      renderedLinks.indexOf("Zoe Harbor"),
    );
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
    await selectDashboardTab("Links");

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
    ]);
    const suggestionItems = within(suggestions).getAllByRole("listitem");
    expect(suggestionItems[0]).toHaveTextContent("Grace Moonrise");
    expect(suggestionItems[1]).toHaveTextContent("Mira Moon");
    expect(suggestionItems[0]).toHaveTextContent(
      "TG: Grace Moonrise (telegram-3)",
    );
    expect(suggestionItems[0]).toHaveTextContent(
      "IG: Grace Moonrise (instagram-4)",
    );
    expect(
      suggestionItems[0].querySelectorAll(
        ".bg-platform-telegram-background, .bg-platform-instagram-background",
      ),
    ).toHaveLength(2);
    expect(suggestionItems[2]).toHaveTextContent("Alexandria Starling");
    expect(suggestionItems[3]).toHaveTextContent("Alex Star");
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
    await selectDashboardTab("Links");

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
    const user = userEvent.setup();
    api.getOverview.mockResolvedValue({
      ...overview,
      total_imported_accounts: 2,
      total_chats: 2,
      total_messages: 70,
      imported_accounts: [
        {
          id: 1,
          platform: "telegram",
          name: "First account",
          username: "first",
          platform_user_id: "platform-1",
          total_messages: 30,
          total_contacts: 4,
        },
        {
          id: 2,
          platform: "telegram",
          name: "Second account",
          username: "second",
          platform_user_id: "platform-2",
          total_messages: 40,
          total_contacts: 7,
        },
      ],
    });
    api.getChats.mockResolvedValue(paginated([
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
    ]));
    api.getContacts.mockResolvedValue(paginated([
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
        personal_chat_messages_sent: 18,
        group_chat_messages_sent: 6,
        ordinary_messages_sent: 22,
        service_events_attributed: 2,
      },
    ]));

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
        name: /Second account chat.*TG: Anton Malkov/,
      }),
    ).toBeInTheDocument();
    const chatPicker = within(chatRegion).getByRole("button", {
      name: "Choose a chat",
    });
    await user.click(chatPicker);
    const chatOptions = screen.getByRole("listbox", {
      name: "Choose a chat options",
    });
    const secondChatOption = within(chatOptions).getByRole("option", {
      name: /TG: Second account chat/,
    });
    expect(
      secondChatOption.querySelector(".bg-platform-telegram-background"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", {
        name: "Choose a chat platform filter",
      }).querySelector('option[value="telegram"]'),
    ).not.toHaveClass("bg-platform-telegram-background");
    await user.click(secondChatOption);
    expect(chatPicker).toHaveTextContent("TG: Second account chat");

    await selectDashboardTab("Contacts");
    const contactsRegion = screen.getByRole("region", {
      name: "Contacts & senders",
    });
    const combinedContactRows = within(contactsRegion).getAllByRole("row", {
      name: /Avery/,
    });
    expect(combinedContactRows).toHaveLength(1);
    expect(within(combinedContactRows[0]).getByText("TG@anton")).toBeInTheDocument();
    expect(
      within(combinedContactRows[0]).getByText("TG: Anton Malkov"),
    ).toBeInTheDocument();
    expect(
      combinedContactRows[0].querySelectorAll(
        ".bg-platform-telegram-background",
      ),
    ).toHaveLength(2);
    expect(combinedContactRows[0]).toHaveTextContent("24");
    await selectDashboardTab("Overview");
    const sourceAccountsCard = within(
      screen.getByRole("tabpanel", { name: "Overview" }),
    )
      .getByRole("heading", { name: "Source accounts" })
      .closest("article");
    expect(sourceAccountsCard).toHaveTextContent("2");
    const overviewRegion = screen.getByRole("region", { name: "Overview" });
    expect(within(overviewRegion).getByRole("row", {
      name: /telegram.*1.*30.*4/,
    })).toBeInTheDocument();
    expect(within(overviewRegion).getByRole("row", {
      name: /telegram.*2.*40.*7/,
    })).toBeInTheDocument();
    expect(within(overviewRegion).getByRole("row", {
      name: /First account.*first.*platform-1/,
    })).toBeInTheDocument();
    expect(within(overviewRegion).getByRole("row", {
      name: /Second account.*second.*platform-2/,
    })).toBeInTheDocument();
    expect(
      within(overviewRegion).getByRole("columnheader", {
        name: "Platform user ID",
      }),
    ).toBeInTheDocument();
    const metricCards = within(overviewRegion).getByText("Source accounts")
      .closest("div.grid");
    expect(metricCards).toHaveClass("grid-cols-6");
  });
});
