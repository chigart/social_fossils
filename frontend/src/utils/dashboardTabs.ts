import { dashboardTabs } from "../constants";

export type DashboardTab = (typeof dashboardTabs)[number]["id"];

export function dashboardTabFromHash(hash: string): DashboardTab {
  const hashTab = hash.slice(1);
  const tab = dashboardTabs.find(({ id }) => id === hashTab);
  return tab?.id ?? "overview";
}
