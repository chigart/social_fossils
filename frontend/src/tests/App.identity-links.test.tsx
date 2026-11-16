import {
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardApi } from "./dashboardTestHelpers";
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
  getCloseFriendsTimeline: vi.fn(),
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

  it("suggests links for exact and one-symbol transliterated name matches", async () => {
    const identities = [
      {
        identity_id: 1,
        platform: "telegram",
        platform_user_id: "telegram-anton",
        identity_group_id: null,
        is_owner: false,
        contacts: [{
          contact_id: 1,
          account_id: 1,
          account_label: "Telegram",
          platform: "telegram",
          display_name: "Anton Malkov",
          username: null,
        }],
      },
      {
        identity_id: 2,
        platform: "instagram",
        platform_user_id: "instagram-anton",
        identity_group_id: null,
        is_owner: false,
        contacts: [{
          contact_id: 2,
          account_id: 2,
          account_label: "Instagram",
          platform: "instagram",
          display_name: "Антон Мальков",
          username: null,
        }],
      },
      {
        identity_id: 3,
        platform: "telegram",
        platform_user_id: "telegram-nikolai",
        identity_group_id: null,
        is_owner: false,
        contacts: [{
          contact_id: 3,
          account_id: 1,
          account_label: "Telegram",
          platform: "telegram",
          display_name: "Nikolai Zaytsev",
          username: null,
        }],
      },
      {
        identity_id: 4,
        platform: "instagram",
        platform_user_id: "instagram-nikolai",
        identity_group_id: null,
        is_owner: false,
        contacts: [{
          contact_id: 4,
          account_id: 2,
          account_label: "Instagram",
          platform: "instagram",
          display_name: "Николай Зайцев",
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
    const suggestionItems = within(suggestions).getAllByRole("listitem");
    expect(suggestionItems).toHaveLength(2);
    expect(suggestionItems[0]).toHaveTextContent(
      "Transliterated Full Name match:",
    );
    expect(suggestionItems[0]).toHaveTextContent("Anton Malkov");
    expect(suggestionItems[0]).toHaveTextContent("Антон Мальков");
    expect(suggestionItems[1]).toHaveTextContent(
      "1-symbol transliterated Full Name difference:",
    );
    expect(suggestionItems[1]).toHaveTextContent("Nikolai Zaytsev");
    expect(suggestionItems[1]).toHaveTextContent("Николай Зайцев");
  });

  it("uses only the name before a pipe when suggesting links", async () => {
    const identities = [
      {
        identity_id: 1,
        platform: "telegram",
        platform_user_id: "telegram-grigoriy",
        identity_group_id: null,
        is_owner: false,
        contacts: [{
          contact_id: 1,
          account_id: 1,
          account_label: "Telegram",
          platform: "telegram",
          display_name: "Grigoriy Chshukin | Alpine climber | Jasa Team",
          username: null,
        }],
      },
      {
        identity_id: 2,
        platform: "instagram",
        platform_user_id: "instagram-grigoriy",
        identity_group_id: null,
        is_owner: false,
        contacts: [{
          contact_id: 2,
          account_id: 2,
          account_label: "Instagram",
          platform: "instagram",
          display_name: "Grigoriy Chshukin | Photographer | Other Team",
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
    expect(within(suggestions).getAllByRole("listitem")).toHaveLength(1);
    expect(suggestions).toHaveTextContent("Grigoriy Chshukin | Alpine climber");
    expect(suggestions).toHaveTextContent("Grigoriy Chshukin | Photographer");
  });

});
