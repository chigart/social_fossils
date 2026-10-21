export const dashboardTabs = [
  { id: "overview", label: "Overview" },
  { id: "chats", label: "Chats" },
  { id: "contacts", label: "Contacts" },
  { id: "communication-balance", label: "Balance" },
  { id: "forgotten-contacts", label: "Forgotten" },
  { id: "communication-timeline", label: "Timeline" },
] as const;

export type DashboardTab = (typeof dashboardTabs)[number]["id"];

export function dashboardTabFromHash(hash: string): DashboardTab {
  const tab = dashboardTabs.find(({ id }) => id === hash.slice(1));
  return tab?.id ?? "overview";
}
