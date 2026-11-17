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

describe("multiple accounts", () => {
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
          total_text_length: 1_500,
          total_contacts: 4,
          earliest_message_timestamp: "2022-01-01T12:00:00Z",
          latest_message_timestamp: "2023-01-01T12:00:00Z",
        },
        {
          id: 2,
          platform: "telegram",
          name: "Second account",
          username: "second",
          platform_user_id: "platform-2",
          total_messages: 40,
          total_text_length: 2_500,
          total_contacts: 7,
          earliest_message_timestamp: "2023-01-01T12:00:00Z",
          latest_message_timestamp: "2024-01-01T12:00:00Z",
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
        name: "Filter chats by platform",
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
    expect(within(combinedContactRows[0]).getAllByRole("cell").map((cell) => cell.textContent))
      .toEqual(["12345", "ActiveClose", "TG@antonTG: Anton Malkov", "18", "6"]);
    await selectDashboardTab("Overview");
    const overviewRegion = screen.getByRole("region", { name: "Overview" });
    expect(within(overviewRegion).queryByText("Source accounts")).not.toBeInTheDocument();
    expect(within(overviewRegion).getByRole("row", {
      name: /telegram.*First account.*first.*30.*1,500.*Jan 1, 2022.*Jan 1, 2023.*4/,
    })).toBeInTheDocument();
    expect(within(overviewRegion).getByRole("row", {
      name: /telegram.*Second account.*second.*40.*2,500.*Jan 1, 2023.*Jan 1, 2024.*7/,
    })).toBeInTheDocument();
    expect(within(overviewRegion).queryByRole("columnheader", {
      name: "Account ID",
    })).not.toBeInTheDocument();
    expect(within(overviewRegion).queryByRole("columnheader", {
      name: "Platform user ID",
    })).not.toBeInTheDocument();
    expect(within(overviewRegion).getByRole("columnheader", {
      name: "Text volume",
    })).toBeInTheDocument();
    expect(within(overviewRegion).getByRole("columnheader", {
      name: "Activity interval",
    })).toBeInTheDocument();
  });
});
