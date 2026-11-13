import {
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardApi } from "./dashboardTestHelpers";
import {
  renderLoadedDashboard,
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
  it("loads analytics on first tab visit and reuses results on revisits", async () => {
    render(<App />);

    await screen.findByText("All messages");
    expect(api.getOverview).toHaveBeenCalledTimes(1);
    expect(api.getChats).not.toHaveBeenCalled();
    expect(api.getChatInsights).not.toHaveBeenCalled();
    expect(api.getContacts).not.toHaveBeenCalled();
    expect(api.getCommunicationBalance).not.toHaveBeenCalled();
    expect(api.getForgottenContacts).not.toHaveBeenCalled();
    expect(api.getIdentityLinks).not.toHaveBeenCalled();
    expect(document.querySelector("#chats")).toBeNull();

    await selectDashboardTab("Chats");
    await waitFor(() => expect(api.getChats).toHaveBeenCalledTimes(1));
    expect(api.getOverview).toHaveBeenCalledTimes(1);
    expect(document.querySelector("#chats")).not.toBeNull();

    await selectDashboardTab("Overview");
    await selectDashboardTab("Chats");
    expect(api.getChats).toHaveBeenCalledTimes(1);
  });

  it("loads only the analytics needed by a directly linked tab", async () => {
    window.history.replaceState(null, "", "/#identity-links");
    render(<App />);

    await waitFor(() => expect(api.getIdentityLinks).toHaveBeenCalledTimes(1));
    expect(api.getOverview).not.toHaveBeenCalled();
    expect(api.getChats).not.toHaveBeenCalled();
    expect(api.getChatInsights).not.toHaveBeenCalled();
    expect(api.getContacts).not.toHaveBeenCalled();
    expect(api.getCommunicationBalance).not.toHaveBeenCalled();
    expect(api.getForgottenContacts).not.toHaveBeenCalled();
    expect(document.querySelector("#overview")).toBeNull();
  });

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

  it("preserves import form state when switching dashboard tabs", async () => {
    const user = userEvent.setup();
    await renderLoadedDashboard();
    await selectDashboardTab("Import");
    await user.selectOptions(
      screen.getByLabelText("Messaging platform"),
      "vk",
    );

    await selectDashboardTab("Chats");
    await selectDashboardTab("Import");

    expect(screen.getByLabelText("Messaging platform")).toHaveValue("vk");
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
    expect(
      within(linkedGroup as HTMLElement).getByText(
        "TG: telegram-user-1 (telegram-user-1)",
      ),
    ).toHaveClass("bg-platform-telegram-background");
    expect(
      within(linkedGroup as HTMLElement).getByText(
        "IG: instagram-user-1 (instagram-user-1)",
      ),
    ).toHaveClass("bg-platform-instagram-background");
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
});
