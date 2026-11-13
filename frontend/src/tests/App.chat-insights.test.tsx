import {
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardApi } from "./dashboardTestHelpers";
import {
  chatInsights,
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
  it("opens insights for the clicked chat title", async () => {
    const user = userEvent.setup();
    api.getChatInsights.mockResolvedValue({
      chats: [{
        ...chatInsights.chats[0],
        chat_id: 2,
        title: "Aurora group",
      }],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Chats");

    await user.click(screen.getByRole("button", { name: "Aurora group" }));

    expect(
      screen.getByRole("tab", { name: "Insights" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(window.location.hash).toBe("#conversation-insights");
    expect(api.getChatInsights).toHaveBeenLastCalledWith(2);
    expect(
      await screen.findByRole("button", { name: "Choose an insight chat" }),
    ).toHaveTextContent("Aurora group");
    expect(screen.getByText("Most popular words")).toBeInTheDocument();
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
    await selectDashboardTab("Insights");

    expect(
      screen.getByRole("heading", { name: "Chat insights" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choose an insight chat" }));
    expect(
      within(
        screen.getByRole("listbox", { name: "Choose an insight chat options" }),
      ).getAllByRole("option"),
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
      within(
        screen.getByRole("listbox", { name: "Choose an insight chat options" }),
      ).getByRole("option", { name: /One-to-one chat/ }),
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
    await selectDashboardTab("Insights");

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

  it("hides message-type and reaction sections for VK insight chats", async () => {
    api.getChatInsights.mockResolvedValue({
      chats: [{ ...chatInsights.chats[0], platform: "vk" }],
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Insights");

    expect(screen.getByText("Conversation flow")).toBeInTheDocument();
    expect(screen.getByText("Most popular words")).toBeInTheDocument();
    expect(screen.queryByText("Message type breakdown")).not.toBeInTheDocument();
    expect(screen.queryByText("Reaction patterns")).not.toBeInTheDocument();
  });

  it("sorts insight chat choices and applies selection only after choosing one", async () => {
    const user = userEvent.setup();
    const mediumChat = {
      ...chatInsights.chats[0],
      chat_id: 10,
      title: "Medium chat",
      ordinary_message_count: 20,
    };
    const oneToOneChat = {
      ...chatInsights.chats[0],
      chat_id: 11,
      title: "One-to-one chat",
      ordinary_message_count: 5,
    };
    const mostActiveChat = {
      ...chatInsights.chats[0],
      chat_id: 12,
      title: "Most active chat",
      ordinary_message_count: 30,
    };
    const insightOptions = [
      mostActiveChat,
      mediumChat,
      oneToOneChat,
    ].map((chat) => ({
      value: String(chat.chat_id),
      label: chat.title,
      platforms: [chat.platform],
      search_terms: [String(chat.chat_id)],
    }));
    api.getChatInsights
      .mockResolvedValueOnce({ chats: [mostActiveChat], options: insightOptions })
      .mockResolvedValueOnce({ chats: [oneToOneChat], options: insightOptions });
    await renderLoadedDashboard();
    await selectDashboardTab("Insights");

    expect(
      screen.queryByRole("navigation", { name: "Pagination" }),
    ).not.toBeInTheDocument();
    const chooser = screen.getByRole("button", { name: "Choose an insight chat" });
    await user.click(chooser);
    const options = within(
      screen.getByRole("listbox", { name: "Choose an insight chat options" }),
    );
    const optionLabels = options
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(optionLabels[0]).toContain("Most active chat");
    expect(optionLabels[1]).toContain("Medium chat");
    expect(optionLabels[2]).toContain("One-to-one chat");

    await user.type(
      screen.getByRole("searchbox", { name: "Choose an insight chat search" }),
      "one-to-one",
    );
    const filteredResults = options.getAllByRole("option");
    expect(filteredResults).toHaveLength(1);
    expect(filteredResults[0]).toHaveTextContent("One-to-one chat");
    expect(
      within(screen.getByRole("region", { name: "Chat insights" }))
        .getByRole("heading", { name: "Ordinary messages" })
        .closest("article"),
    ).toHaveTextContent("30");
    await user.click(filteredResults[0]);

    expect(
      within(screen.getByRole("region", { name: "Chat insights" }))
        .getByRole("heading", { name: "Ordinary messages" })
        .closest("article"),
    ).toHaveTextContent("5");

    expect(chooser).toHaveTextContent("One-to-one chat");
  });

  it("keeps the insight chat picker open while interacting with its options scrollbar", async () => {
    const user = userEvent.setup();
    api.getChatInsights.mockResolvedValue({
      chats: [{
        ...chatInsights.chats[0],
        chat_id: 1,
        title: "Chat 1",
      }],
      options: Array.from({ length: 20 }, (_, index) => ({
        value: String(index + 1),
        label: `Chat ${index + 1}`,
        platforms: ["telegram"],
        search_terms: [String(index + 1)],
      })),
    });
    await renderLoadedDashboard();
    await selectDashboardTab("Insights");
    await user.click(screen.getByRole("button", { name: "Choose an insight chat" }));

    const options = screen.getByRole("listbox", {
      name: "Choose an insight chat options",
    });
    const search = screen.getByRole("searchbox", {
      name: "Choose an insight chat search",
    });
    fireEvent.mouseDown(options);
    fireEvent.blur(search, { relatedTarget: null });

    expect(options).toBeInTheDocument();
  });

  it("shows loading status while the active overview request is pending", () => {
    api.getOverview.mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getAllByRole("status")).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent("Loading analytics…");
    expect(api.getChatInsights).not.toHaveBeenCalled();
    expect(api.getChats).not.toHaveBeenCalled();
  });
});
