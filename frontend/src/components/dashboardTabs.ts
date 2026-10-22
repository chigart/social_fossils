export const dashboardTabs = [
  { id: "overview", label: "Overview" },
  { id: "chat-insights", label: "Insights" },
  { id: "chats", label: "Chats" },
  { id: "contacts", label: "Contacts" },
  { id: "communication-balance", label: "Balance" },
  { id: "forgotten-contacts", label: "Forgotten" },
  { id: "communication-timeline", label: "Timeline" },
  { id: "uploads", label: "Import" },
] as const;

export type DashboardTab = (typeof dashboardTabs)[number]["id"];

export function dashboardTabFromHash(hash: string): DashboardTab {
  const tab = dashboardTabs.find(({ id }) => id === hash.slice(1));
  return tab?.id ?? "overview";
}
