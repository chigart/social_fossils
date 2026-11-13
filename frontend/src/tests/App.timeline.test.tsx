import {
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardApi } from "./dashboardTestHelpers";
import {
  chatInsights,
  timeline,
} from "./App.testFixtures";
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
  it("uses one chat selection for the timeline and insight details", async () => {
    const user = userEvent.setup();
    const firstChat = {
      ...chatInsights.chats[0],
      chat_id: 10,
      title: "Private group",
    };
    const secondChat = {
      ...chatInsights.chats[0],
      chat_id: 11,
      title: "One-to-one chat",
      ordinary_message_count: 5,
    };
    const insightOptions = [
      {
        value: "10",
        label: "Private group",
        platforms: ["telegram"],
        search_terms: ["private_group", "10"],
      },
      {
        value: "11",
        label: "One-to-one chat",
        platforms: ["telegram"],
        search_terms: ["personal_chat", "11"],
      },
    ];
    api.getChatInsights
      .mockResolvedValueOnce({ chats: [firstChat], options: insightOptions })
      .mockResolvedValueOnce({ chats: [secondChat], options: insightOptions });
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
    await selectDashboardTab("Insights");

    const region = screen.getByRole("region", {
      name: "Communication timeline",
    });
    expect(
      screen.getByRole("button", { name: "Choose an insight chat" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("combobox", { name: "Timeline scope" }),
    ).not.toBeInTheDocument();
    const chart = await within(region).findByRole("img", {
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

    await user.click(screen.getByRole("button", { name: "Choose an insight chat" }));
    await user.click(
      within(
        screen.getByRole("listbox", { name: "Choose an insight chat options" }),
      ).getByRole("option", { name: /One-to-one chat/ }),
    );

    expect(api.getChatInsights).toHaveBeenNthCalledWith(1, undefined);
    expect(api.getChatInsights).toHaveBeenNthCalledWith(2, 11);
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
    await selectDashboardTab("Insights");

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
