import type {
  ChatInsightSender,
  ChatInsightsStatistics,
  ConversationParticipantCount,
  EmojiFrequency,
  WordFrequency,
} from "../api";
import {
  DEGREES_PER_PERCENTAGE_POINT,
  MINIMUM_REPEATED_ITEM_COUNT,
  PERCENTAGE_SCALE,
  PERCENTAGE_DECIMAL_PLACES,
  TOP_MESSAGE_TYPE_SENDER_COUNT,
  TOP_SENDER_COUNT,
  senderColors,
} from "../constants";

export type SenderShareMetric = "messages" | "characters";

export type SenderAverageLength = {
  key: string;
  label: string;
  messageCount: number;
  textLength: number;
  averageLength: number;
};

export type SenderShareSlice = {
  key: string;
  label: string;
  value: number;
  color: string;
  percentage: number;
  startAngle: number;
  endAngle: number;
};

export function filterRepeatedItems<T extends WordFrequency | EmojiFrequency>(
  items: T[],
) {
  return items.filter((item) => item.count >= MINIMUM_REPEATED_ITEM_COUNT);
}

export function sortChatInsightsChats(chats: ChatInsightsStatistics[]) {
  return [...chats].sort(
    (left, right) =>
      right.ordinary_message_count - left.ordinary_message_count ||
      (left.title ?? "").localeCompare(right.title ?? "") ||
      left.chat_id - right.chat_id,
  );
}

export function filterChatInsightsChats(
  chats: ChatInsightsStatistics[],
  search: string,
) {
  const searchTerm = search.trim().toLocaleLowerCase();
  return chats.filter((chat) =>
    [chat.title, chat.chat_type, chat.source_account_label]
      .filter((value): value is string => value !== null)
      .some((value) => value.toLocaleLowerCase().includes(searchTerm)),
  );
}

export function getSelectedChatInsights(
  sortedChats: ChatInsightsStatistics[],
  selectedChatId: number | null,
) {
  return (
    sortedChats.find((chat) => chat.chat_id === selectedChatId) ?? sortedChats[0]
  );
}

function valueForSender(sender: ChatInsightSender, metric: SenderShareMetric) {
  return metric === "messages" ? sender.message_count : sender.text_length;
}

export function buildSenderShareChart(
  senders: ChatInsightSender[],
  total: number,
  metric: SenderShareMetric,
) {
  const rankedSenders = [...senders].sort(
    (left, right) =>
      valueForSender(right, metric) - valueForSender(left, metric) ||
      left.display_name.localeCompare(right.display_name),
  );
  const visibleSenders = rankedSenders.slice(0, TOP_SENDER_COUNT);
  const otherSendersValue = rankedSenders
    .slice(TOP_SENDER_COUNT)
    .reduce((sum, sender) => sum + valueForSender(sender, metric), 0);
  const sliceValues = [
    ...visibleSenders.map((sender, index) => ({
      key: sender.sender_id ?? sender.display_name,
      label: sender.display_name,
      value: valueForSender(sender, metric),
      color: senderColors[index],
    })),
    ...(rankedSenders.length > TOP_SENDER_COUNT
      ? [
          {
            key: "other-senders",
            label: "Other senders",
            value: otherSendersValue,
            color: "var(--color-chart-other)",
          },
        ]
      : []),
  ];
  let nextAngle = 0;
  const slices: SenderShareSlice[] = sliceValues.map((slice) => {
    const percentage =
      total > 0 ? (slice.value / total) * PERCENTAGE_SCALE : 0;
    const startAngle = nextAngle;
    nextAngle += percentage * DEGREES_PER_PERCENTAGE_POINT;
    return {
      ...slice,
      percentage,
      startAngle,
      endAngle: nextAngle,
    };
  });
  const pieBackground =
    total > 0
      ? `conic-gradient(${slices
          .map(({ color, startAngle, endAngle }) =>
            `${color} ${startAngle}deg ${endAngle}deg`,
          )
          .join(", ")})`
      : "var(--color-chart-empty)";
  const chartDescription = slices
    .map(
      ({ label, percentage }) =>
        `${label} ${percentage.toFixed(PERCENTAGE_DECIMAL_PLACES)}%`,
    )
    .join(", ");

  return { slices, pieBackground, chartDescription };
}

export function buildSenderAverageLengthChart(senders: ChatInsightSender[]) {
  const rankedSenders = senders
    .filter((sender) => sender.message_count > 0)
    .map((sender) => ({
      key: sender.sender_id ?? sender.display_name,
      label: sender.display_name,
      messageCount: sender.message_count,
      textLength: sender.text_length,
      averageLength: sender.text_length / sender.message_count,
    }))
    .sort(
      (left, right) =>
        right.averageLength - left.averageLength ||
        left.label.localeCompare(right.label),
    );

  return {
    senders: rankedSenders,
    maximum: Math.max(0, ...rankedSenders.map(({ averageLength }) => averageLength)),
  };
}

export function buildMessageTypeShareChart(senders: ConversationParticipantCount[]) {
  const topSenders = [...senders]
    .sort(
      (first, second) =>
        second.count - first.count ||
        first.display_name.localeCompare(second.display_name),
    )
    .slice(0, TOP_MESSAGE_TYPE_SENDER_COUNT);
  const total = topSenders.reduce((sum, sender) => sum + sender.count, 0);
  let nextAngle = 0;
  const slices = topSenders.map((sender, index) => {
    const percentage =
      total > 0 ? (sender.count / total) * PERCENTAGE_SCALE : 0;
    const startAngle = nextAngle;
    nextAngle += percentage * DEGREES_PER_PERCENTAGE_POINT;
    return {
      key: sender.sender_id ?? sender.display_name,
      label: sender.display_name,
      value: sender.count,
      color: senderColors[index],
      percentage,
      startAngle,
      endAngle: nextAngle,
    };
  });
  const pieBackground =
    total > 0
      ? `conic-gradient(${slices
          .map(({ color, startAngle, endAngle }) =>
            `${color} ${startAngle}deg ${endAngle}deg`,
          )
          .join(", ")})`
      : "var(--color-chart-empty)";
  const chartDescription = slices
    .map(
      ({ label, percentage }) =>
        `${label} ${percentage.toFixed(PERCENTAGE_DECIMAL_PLACES)}%`,
    )
    .join(", ");

  return { slices, pieBackground, chartDescription };
}
