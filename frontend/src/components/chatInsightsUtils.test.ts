import { describe, expect, it } from "vitest";
import { chatInsights } from "../App.testFixtures";
import {
  buildSenderShareChart,
  filterRepeatedItems,
  filterChatInsightsChats,
  getSelectedChatInsights,
  sortChatInsightsChats,
} from "./chatInsightsUtils";

describe("chat insights utilities", () => {
  it("filters word and emoji frequencies that appear only once", () => {
    expect(
      filterRepeatedItems([
        { word: "often", count: 2 },
        { word: "once", count: 1 },
      ]),
    ).toEqual([{ word: "often", count: 2 }]);
    expect(
      filterRepeatedItems([
        { emoji: "❤️", count: 3 },
        { emoji: "🎉", count: 1 },
      ]),
    ).toEqual([{ emoji: "❤️", count: 3 }]);
  });

  it("sorts chats by message count, title, then ID without mutating input", () => {
    const chats = [
      { ...chatInsights.chats[0], chat_id: 3, title: "Beta", ordinary_message_count: 5 },
      { ...chatInsights.chats[0], chat_id: 2, title: "Alpha", ordinary_message_count: 5 },
      { ...chatInsights.chats[0], chat_id: 1, title: "Alpha", ordinary_message_count: 5 },
      { ...chatInsights.chats[0], chat_id: 4, title: "Most active", ordinary_message_count: 9 },
    ];

    expect(sortChatInsightsChats(chats).map(({ chat_id }) => chat_id)).toEqual([
      4, 1, 2, 3,
    ]);
    expect(chats.map(({ chat_id }) => chat_id)).toEqual([3, 2, 1, 4]);
  });

  it("filters by title, chat type, and account label and falls back to the first sorted chat", () => {
    const chats = [
      { ...chatInsights.chats[0], chat_id: 2, title: "Second", ordinary_message_count: 3 },
      { ...chatInsights.chats[0], chat_id: 1, title: "First", ordinary_message_count: 8 },
    ];

    expect(
      filterChatInsightsChats(chats, "  PRIVATE_GROUP ").map(
        ({ chat_id }) => chat_id,
      ),
    ).toEqual([2, 1]);
    expect(filterChatInsightsChats(chats, "@ANTON")).toHaveLength(2);
    expect(filterChatInsightsChats(chats, "missing")).toEqual([]);
    expect(getSelectedChatInsights(sortChatInsightsChats(chats), 2)?.chat_id).toBe(
      2,
    );
    expect(getSelectedChatInsights(sortChatInsightsChats(chats), null)?.chat_id).toBe(
      1,
    );
  });

  it("ranks the top ten senders and combines the rest in the other slice", () => {
    const senders = Array.from({ length: 11 }, (_, index) => ({
      ...chatInsights.chats[0].senders[0],
      sender_telegram_id: `user-${index}`,
      display_name: `Sender ${index}`,
      message_count: 11 - index,
      text_length: index + 1,
    }));

    const chart = buildSenderShareChart(senders, 66, "messages");

    expect(chart.slices).toHaveLength(11);
    expect(chart.slices[0]).toMatchObject({
      label: "Sender 0",
      value: 11,
      percentage: (11 / 66) * 100,
      startAngle: 0,
    });
    expect(chart.slices[10]).toMatchObject({
      key: "other-senders",
      label: "Other senders",
      value: 1,
      color: "#9299a8",
    });
    expect(chart.chartDescription).toContain("Other senders 1.5%");
    expect(chart.pieBackground).toContain("conic-gradient(");
  });

  it("uses the neutral chart background when the total is zero", () => {
    const chart = buildSenderShareChart(chatInsights.chats[0].senders, 0, "messages");

    expect(chart.pieBackground).toBe("#e7e9ee");
    expect(chart.slices.every(({ percentage }) => percentage === 0)).toBe(true);
  });
});
