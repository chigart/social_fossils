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
  getGroupInteraction: vi.fn(),
  getCommunicationTimeline: vi.fn(),
  getCloseFriendsTimeline: vi.fn(),
  uploadFile: vi.fn(),
}));

vi.mock("../api", () => api);

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  resetDashboardApi(api);
});

describe("Forgotten contacts and interactions", () => {
  it("rechecks group data when returning to the tab", async () => {
    await renderLoadedDashboard();
    await selectDashboardTab("Interactions");
    const region = screen.getByRole("region", { name: "Group interactions" });
    await within(region).findByText("Mika");
    await selectDashboardTab("Forgotten");
    await selectDashboardTab("Interactions");
    expect(api.getForgottenContacts.mock.calls.filter(
      (call) => call[4] === "group",
    )).toHaveLength(2);
  });

  it("loads an off-page participant without requesting another full page", async () => {
    const user = userEvent.setup();
    const target = { ...forgotten.contacts[1], display_name: "Other participant" };
    api.getForgottenContacts.mockResolvedValue({
      ...forgotten,
      options: [
        { value: "0", label: "Mika", platforms: ["telegram"], search_terms: [], contact_id: 41 },
        { value: "50", label: "Other participant", platforms: ["telegram"], search_terms: [], contact_id: 42 },
      ],
      pagination: { page: 1, page_size: 50, total: 51 },
      contacts: [forgotten.contacts[0]],
    });
    api.getGroupInteraction.mockResolvedValue(target);
    await renderLoadedDashboard();
    await selectDashboardTab("Interactions");
    const region = screen.getByRole("region", { name: "Group interactions" });
    await within(region).findByText("Mika");
    await user.click(within(region).getByRole("button", { name: "Choose a participant" }));
    await user.click(within(region).getByRole("option", { name: /Other participant/ }));
    expect(await within(region).findByRole("row", { name: /Other participant/ })).toBeInTheDocument();
    expect(api.getGroupInteraction).toHaveBeenCalledWith(42);
    expect(api.getForgottenContacts).toHaveBeenCalledTimes(1);
    await user.click(within(region).getByRole("button", { name: "Choose a participant" }));
    await user.click(within(region).getByRole("button", { name: "All participants" }));
    expect(await within(region).findByRole("row", { name: /Mika/ })).toBeInTheDocument();
  });

  it("uses the current page for an on-page participant", async () => {
    const user = userEvent.setup();
    api.getForgottenContacts.mockResolvedValue({
      ...forgotten,
      options: [
        { value: "0", label: "Mika", platforms: ["telegram"], search_terms: [], contact_id: 41 },
        { value: "1", label: "Zoe", platforms: ["telegram"], search_terms: [], contact_id: 42 },
      ],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Interactions");
    const region = screen.getByRole("region", { name: "Group interactions" });
    await within(region).findByText("Mika");
    await user.click(within(region).getByRole("button", { name: "Choose a participant" }));
    await user.click(within(region).getByRole("option", { name: /Zoe/ }));
    expect(rowTitles(within(region).getByRole("table"))).toEqual(["Zoe"]);
    expect(api.getGroupInteraction).not.toHaveBeenCalled();
    expect(api.getForgottenContacts).toHaveBeenCalledTimes(1);
  });

  it("reports and retries an individual participant request", async () => {
    const user = userEvent.setup();
    api.getForgottenContacts.mockResolvedValue({
      ...forgotten,
      options: [
        { value: "50", label: "Zoe", platforms: ["telegram"], search_terms: [], contact_id: 42 },
      ],
      pagination: { page: 1, page_size: 50, total: 51 },
      contacts: [forgotten.contacts[0]],
    });
    api.getGroupInteraction.mockRejectedValueOnce(new Error("Participant unavailable."));
    api.getGroupInteraction.mockResolvedValueOnce(forgotten.contacts[1]);
    await renderLoadedDashboard();
    await selectDashboardTab("Interactions");
    const region = screen.getByRole("region", { name: "Group interactions" });
    await within(region).findByText("Mika");
    await user.click(within(region).getByRole("button", { name: "Choose a participant" }));
    await user.click(within(region).getByRole("option", { name: /Zoe/ }));
    expect(await within(region).findByRole("alert")).toHaveTextContent("Participant unavailable.");
    await user.click(within(region).getByRole("button", { name: "Retry" }));
    expect(await within(region).findByRole("row", { name: /Zoe/ })).toBeInTheDocument();
    expect(api.getForgottenContacts).toHaveBeenCalledTimes(1);
  });

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

  it("shows colored platform abbreviations in Forgotten and Interactions", async () => {
    api.getForgottenContacts.mockResolvedValue({
      ...forgotten,
      contacts: [
        {
          ...forgotten.contacts[0],
          platforms: ["telegram", "facebook", "instagram", "vk"],
        },
      ],
    });
    await renderLoadedDashboard();

    for (const tab of ["Forgotten", "Interactions"]) {
      await selectDashboardTab(tab);
      const region = screen.getByRole("region", {
        name: tab === "Forgotten" ? "Forgotten contacts" : "Group interactions",
      });
      const mikaRow = await within(region).findByRole("row", { name: /Mika/ });
      for (const [label, className] of [
        ["TG", "bg-platform-telegram-background"],
        ["FB", "bg-platform-facebook-background"],
        ["IG", "bg-platform-instagram-background"],
        ["VK", "bg-platform-vk-background"],
      ]) {
        expect(within(mikaRow).getByText(label)).toHaveClass(className);
      }
    }
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
