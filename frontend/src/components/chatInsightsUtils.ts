import type {
  ChatInsightSender,
  ChatInsightsStatistics,
} from "../api";

const senderColors = [
  "#5267d8",
  "#d46c5c",
  "#36a58b",
  "#d59b38",
  "#8b61bc",
  "#3f92bd",
  "#bf5f91",
  "#789449",
  "#c45b47",
  "#4d7882",
];

export type SenderShareMetric = "messages" | "characters";

export type SenderShareSlice = {
  key: string;
  label: string;
  value: number;
  color: string;
  percentage: number;
  startAngle: number;
  endAngle: number;
};

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
  const visibleSenders = rankedSenders.slice(0, 10);
  const otherSendersValue = rankedSenders
    .slice(10)
    .reduce((sum, sender) => sum + valueForSender(sender, metric), 0);
  const sliceValues = [
    ...visibleSenders.map((sender, index) => ({
      key: sender.sender_telegram_id ?? "unknown",
      label: sender.display_name,
      value: valueForSender(sender, metric),
      color: senderColors[index],
    })),
    ...(rankedSenders.length > 10
      ? [
          {
            key: "other-senders",
            label: "Other senders",
            value: otherSendersValue,
            color: "#9299a8",
          },
        ]
      : []),
  ];
  let nextAngle = 0;
  const slices: SenderShareSlice[] = sliceValues.map((slice) => {
    const percentage = total > 0 ? (slice.value / total) * 100 : 0;
    const startAngle = nextAngle;
    nextAngle += percentage * 3.6;
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
      : "#e7e9ee";
  const chartDescription = slices
    .map(({ label, percentage }) => `${label} ${percentage.toFixed(1)}%`)
    .join(", ");

  return { slices, pieBackground, chartDescription };
}
