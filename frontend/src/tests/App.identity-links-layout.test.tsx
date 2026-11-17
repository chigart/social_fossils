import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardApi } from "./dashboardTestHelpers";
import { selectDashboardTab } from "./App.testUtils";
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
  getOwnerReplyTimeline: vi.fn(),
  uploadFile: vi.fn(),
}));

vi.mock("../api", () => api);

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  resetDashboardApi(api);
});

describe("identity links layout", () => {
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
});
