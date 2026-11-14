import {
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardApi } from "./dashboardTestHelpers";
import { forgotten } from "./App.testFixtures";
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

describe("Forgotten contacts and interactions", () => {
  it("loads private Forgotten and group Interactions scopes separately", async () => {
    api.getForgottenContacts.mockImplementation(
      async (_page, _pageSize, _sortBy, _sortDirection, scope) =>
        scope === "group"
          ? {
              ...forgotten,
              summary: { ...forgotten.summary, eligible_contacts: 1 },
              pagination: { ...forgotten.pagination, total: 1 },
              contacts: [
                {
                  ...forgotten.contacts[0],
                  display_name: "Group participant",
                  interaction_chat_count: 4,
                },
              ],
            }
          : forgotten,
    );
    await renderLoadedDashboard();

    await selectDashboardTab("Interactions");
    const interactions = await screen.findByRole("region", {
      name: "Group interactions",
    });
    expect(api.getForgottenContacts).toHaveBeenLastCalledWith(
      1,
      50,
      "ranking_score",
      "desc",
      "group",
    );
    expect(
      within(interactions).getByRole("row", {
        name: /Group participant.*4/,
      }),
    ).toBeInTheDocument();
    expect(
      within(interactions).getByRole("columnheader", { name: "Group chats" }),
    ).toBeInTheDocument();

    await selectDashboardTab("Forgotten");
    const forgottenRegion = screen.getByRole("region", {
      name: "Forgotten contacts",
    });
    expect(api.getForgottenContacts).toHaveBeenLastCalledWith(
      1,
      50,
      "ranking_score",
      "desc",
      "private",
    );
    expect(
      within(forgottenRegion).getByRole("row", { name: /Mika/ }),
    ).toBeInTheDocument();
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
    await user.click(within(region).getByRole("button", {
      name: "Choose a forgotten contact",
    }));
    await user.click(
      within(
        screen.getByRole("listbox", {
          name: "Choose a forgotten contact options",
        }),
      ).getByRole("option", { name: /Zoe/ }),
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
    await user.click(within(region).getByRole("button", {
      name: "Choose a forgotten contact",
    }));
    await user.type(
      within(region).getByRole("searchbox", {
        name: "Choose a forgotten contact search",
      }),
      "nobody",
    );
    expect(
      within(region).getByText("No contacts match these filters."),
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
});
