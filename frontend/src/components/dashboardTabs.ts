export const dashboardTabs = [
  { id: "overview", label: "Overview" },
  { id: "conversation-insights", label: "Conversation insights" },
  { id: "chats", label: "Chats" },
  { id: "contacts", label: "Contacts" },
  { id: "communication-balance", label: "Balance" },
  { id: "forgotten-contacts", label: "Forgotten" },
  { id: "uploads", label: "Import" },
] as const;

export type DashboardTab = (typeof dashboardTabs)[number]["id"];

export function dashboardTabFromHash(hash: string): DashboardTab {
  const hashTab = hash.slice(1);
  if (hashTab === "chat-insights" || hashTab === "communication-timeline") {
    return "conversation-insights";
  }
  const tab = dashboardTabs.find(({ id }) => id === hashTab);
  return tab?.id ?? "overview";
}
