import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  balance,
  chats,
  contacts,
  emptyBalanceSummary,
  forgotten,
  overview,
  timeline,
} from "./App.testFixtures";
import {
  renderLoadedDashboard,
  rowTitles,
  selectDashboardTab,
} from "./App.testUtils";
import App from "../App";
import { DEFAULT_PAGE_SIZE } from "../constants";

const api = vi.hoisted(() => ({
  getOverview: vi.fn(),
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
}));

vi.mock("../api", () => api);

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  Object.values(api).forEach((mock) => mock.mockReset());
  api.getOverview.mockResolvedValue(overview);
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

async function renderBalanceDashboard() {
  await renderLoadedDashboard();
  await selectDashboardTab("Balance");
}

describe("communication balance dashboard", () => {
  it("retries a failed communication balance request without crashing other sections", async () => {
    const user = userEvent.setup();
    api.getCommunicationBalance.mockRejectedValueOnce(
      new Error("Balance analytics unavailable."),
    );
    render(<App />);
    await selectDashboardTab("Balance");
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });

    expect(await within(balanceRegion).findByRole("alert")).toHaveTextContent(
      "Balance analytics unavailable.",
    );
    expect(document.getElementById("overview-panel")).toHaveAttribute("hidden");
    await user.click(within(balanceRegion).getByRole("button", { name: "Retry" }));

    expect(
      await within(balanceRegion).findByRole("row", { name: /Alex/ }),
    ).toBeInTheDocument();
    expect(api.getCommunicationBalance).toHaveBeenCalledTimes(2);
  });

  it("shows the eligible-contact empty state when the API has no results", async () => {
    api.getCommunicationBalance.mockResolvedValue({
      summary: emptyBalanceSummary,
      contacts: [],
      pagination: { page: 1, page_size: DEFAULT_PAGE_SIZE, total: 0 },
    });
    render(<App />);
    await selectDashboardTab("Balance");

    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    expect(
      await within(balanceRegion).findByRole("heading", {
        name: "No eligible contacts available",
      }),
    ).toBeInTheDocument();
    expect(
      within(balanceRegion).getByText("Eligible contacts").parentElement,
    ).toHaveTextContent("0");
  });

  it("renders summary values directly from the communication balance API", async () => {
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });

    for (const [label, value] of [
      ["Eligible contacts", "5"],
      ["Balanced", "1"],
      ["Mostly owner", "1"],
      ["Mostly contact", "1"],
      ["Strongly owner", "1"],
      ["Strongly contact", "0"],
      ["Insufficient data", "1"],
      ["Total text exchanged", "3,700"],
    ]) {
      expect(
        within(balanceRegion).getByText(label, { selector: "h3" }).parentElement,
      ).toHaveTextContent(value);
    }
  });

  it("shows text volume, API shares, date values, and supplementary message counts", async () => {
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const alexRow = within(balanceRegion).getByRole("row", { name: /Alex/ });

    expect(alexRow).toHaveTextContent("1,000");
    expect(alexRow).toHaveTextContent("500");
    expect(alexRow).toHaveTextContent("Balanced");
    expect(alexRow).toHaveTextContent("1");
    expect(alexRow).toHaveTextContent("5");
    const alexShare = within(alexRow).getByRole("img", {
      name: "Owner 50%, contact 50%",
    });
    const alexBar = alexShare.querySelectorAll(".flex")[1];
    expect(alexBar?.children[0]).toHaveStyle({ width: "50%" });
    expect(alexBar?.children[1]).toHaveStyle({ width: "50%" });

    const coraRow = within(balanceRegion).getByRole("row", { name: /Cora/ });
    const coraShare = within(coraRow).getByRole("img", {
      name: "Owner 25%, contact 75%",
    });
    const coraBar = coraShare.querySelectorAll(".flex")[1];
    expect(coraBar?.children[0]).toHaveStyle({ width: "25%" });
    expect(coraBar?.children[1]).toHaveStyle({ width: "75%" });
    expect(
      balanceRegion,
    ).toHaveTextContent("Text volume counts Unicode code points");
    expect(balanceRegion).toHaveTextContent("First seen");
    expect(balanceRegion).toHaveTextContent("Last seen");
  });

  it("shows colored platform abbreviations beside each contact name", async () => {
    api.getCommunicationBalance.mockResolvedValue({
      ...balance,
      contacts: [
        {
          ...balance.contacts[0],
          platforms: ["telegram", "facebook", "instagram", "vk"],
        },
      ],
    });
    await renderBalanceDashboard();

    const alexRow = within(
      screen.getByRole("region", { name: "Communication balance" }),
    ).getByRole("row", { name: /Alex/ });
    for (const [label, className] of [
      ["TG", "bg-platform-telegram-background"],
      ["FB", "bg-platform-facebook-background"],
      ["IG", "bg-platform-instagram-background"],
      ["VK", "bg-platform-vk-background"],
    ]) {
      expect(within(alexRow).getByText(label)).toHaveClass(className);
    }
  });

  it("filters contacts by classification and applies the selected name", async () => {
    const user = userEvent.setup();
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const classificationFilter = within(balanceRegion).getByRole("combobox", {
      name: "Filter by classification",
    });

    await user.selectOptions(classificationFilter, "mostly_owner");
    expect(within(balanceRegion).getAllByRole("row")).toHaveLength(2);
    expect(within(balanceRegion).getByRole("row", { name: /Bea/ })).toBeInTheDocument();
    expect(within(balanceRegion).queryByRole("row", { name: /Alex/ })).not.toBeInTheDocument();

    await user.selectOptions(classificationFilter, "all");
    const table = within(balanceRegion).getByRole("table");
    const originalRows = within(table).getAllByRole("row").length;
    await user.click(
      within(balanceRegion).getByRole("button", {
        name: "Choose a balance contact",
      }),
    );
    await user.type(
      within(balanceRegion).getByRole("searchbox", {
        name: "Choose a balance contact search",
      }),
      "cOrA",
    );
    expect(within(table).getAllByRole("row")).toHaveLength(originalRows);
    await user.click(
      within(
        screen.getByRole("listbox", {
          name: "Choose a balance contact options",
        }),
      ).getByRole("option", { name: /Cora/ }),
    );
    expect(within(balanceRegion).getAllByRole("row")).toHaveLength(2);
    expect(within(balanceRegion).getByRole("row", { name: /Cora/ })).toBeInTheDocument();
  });

  it("sorts by total text volume, not message counts", async () => {
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const sortBy = within(balanceRegion).getByRole("combobox", {
      name: "Sort contacts by",
    });
    const table = within(balanceRegion).getByRole("table");

    expect(rowTitles(table)).toEqual([
      "Cora",
      "Alex",
      "Drew",
      "Bea",
      "Zero text",
    ]);
    await userEvent.setup().selectOptions(sortBy, "owner_share");
    expect(rowTitles(table)).toEqual([
      "Drew",
      "Bea",
      "Alex",
      "Cora",
      "Zero text",
    ]);
  });

  it("sorts owner text share in the selected direction and keeps missing shares last", async () => {
    const user = userEvent.setup();
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    await user.selectOptions(
      within(balanceRegion).getByRole("combobox", { name: "Sort contacts by" }),
      "owner_share",
    );
    await user.selectOptions(
      within(balanceRegion).getByRole("combobox", { name: "Sort direction" }),
      "asc",
    );

    expect(rowTitles(within(balanceRegion).getByRole("table"))).toEqual([
      "Cora",
      "Alex",
      "Bea",
      "Drew",
      "Zero text",
    ]);
  });

  it("sorts most recent activity with undated contacts last", async () => {
    const user = userEvent.setup();
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    await user.selectOptions(
      within(balanceRegion).getByRole("combobox", { name: "Sort contacts by" }),
      "recent_activity",
    );

    expect(rowTitles(within(balanceRegion).getByRole("table"))).toEqual([
      "Drew",
      "Cora",
      "Bea",
      "Alex",
      "Zero text",
    ]);
  });

  it("marks insufficient-data contacts distinctly and avoids invalid zero-volume shares", async () => {
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const zeroRow = within(balanceRegion).getByRole("row", { name: /Zero text/ });

    expect(zeroRow).toHaveTextContent("Insufficient data");
    expect(zeroRow).toHaveTextContent("Less than 500 characters");
    expect(zeroRow).toHaveTextContent("No text volume to compare");
    expect(zeroRow).toHaveTextContent("Owner — · Contact —");
    expect(zeroRow).not.toHaveTextContent("NaN");
    expect(zeroRow).not.toHaveTextContent("Infinity");
  });

  it("keeps the balance table scrollable and controls usable on narrow screens", async () => {
    await renderBalanceDashboard();
    const balanceRegion = screen.getByRole("region", {
      name: "Communication balance",
    });
    const table = within(balanceRegion).getByRole("table");

    expect(table).toHaveClass("min-w-[1050px]");
    expect(
      within(balanceRegion).getByRole("region", {
        name: "Scrollable communication balance table",
      }),
    ).toHaveClass("overflow-x-scroll");
    expect(
      within(balanceRegion).getByRole("combobox", { name: "Sort direction" }),
    ).toBeVisible();
    expect(
      within(balanceRegion).getByRole("button", {
        name: "Choose a balance contact",
      }),
    ).toBeVisible();
  });
});
