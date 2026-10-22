import { useState } from "react";
import type { ChatInsightsResponse } from "../api";
import type { Resource } from "../types";
import {
  filterChatInsightsChats,
  getSelectedChatInsights,
  sortChatInsightsChats,
} from "./chatInsightsUtils";

export function useChatInsightsView(
  insights: Resource<ChatInsightsResponse>,
  selectedChatId: number | null,
) {
  const [chatSearch, setChatSearch] = useState("");
  const chats = insights.data?.chats ?? [];
  const sortedChats = sortChatInsightsChats(chats);

  return {
    chatSearch,
    trimmedChatSearch: chatSearch.trim(),
    onChatSearchChange: (value: string) => setChatSearch(value),
    matchingChats: filterChatInsightsChats(sortedChats, chatSearch),
    selectedChat: getSelectedChatInsights(sortedChats, selectedChatId),
  };
}
