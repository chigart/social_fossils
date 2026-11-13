import type { KeyboardEvent } from "react";
import { Button } from "./Button";
import { dashboardTabs } from "../constants";
import type { DashboardTab } from "../utils/dashboardTabs";

export function DashboardHeader({
  selectedTab,
  onTabSelect,
}: {
  selectedTab: DashboardTab;
  onTabSelect: (tab: DashboardTab) => void;
}) {
  const selectByKeyboard = (
    event: KeyboardEvent<HTMLButtonElement>,
    currentIndex: number,
  ) => {
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % dashboardTabs.length;
    if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + dashboardTabs.length) % dashboardTabs.length;
    }
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = dashboardTabs.length - 1;
    if (nextIndex === undefined) return;

    event.preventDefault();
    const nextTab = dashboardTabs[nextIndex];
    selectTab(nextTab.id);
    document.getElementById(`${nextTab.id}-tab`)?.focus();
  };

  const selectTab = (tab: DashboardTab) => {
    onTabSelect(tab);
    window.history.pushState(null, "", `#${tab}`);
  };

  return (
    <header className="flex min-h-[70px] flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-border bg-surface px-[max(28px,calc((100vw-1200px)/2))] py-3 max-sm:flex-col max-sm:items-stretch max-sm:px-4">
      <a
        className="inline-flex items-center gap-2.5 self-center font-sans text-logo font-extrabold text-ink no-underline max-sm:gap-[7px] max-sm:text-subheading"
        href="#overview"
        aria-label="Social Fossils dashboard home"
      >
        <span
          className="grid size-8 place-items-center rounded-[10px] bg-surface-brand text-small tracking-[-0.04em] text-brand-strong max-sm:size-7"
          aria-hidden="true"
        >
          SF
        </span>
        <span>Social Fossils</span>
      </a>
      <nav
        aria-label="Dashboard sections"
      >
        <div
          className="flex flex-wrap justify-end gap-1.5 max-sm:justify-center"
          role="tablist"
          aria-label="Dashboard sections"
        >
          {dashboardTabs.map((tab, index) => (
            <Button
              id={`${tab.id}-tab`}
              key={tab.id}
              active={selectedTab === tab.id}
              variant="tab"
              type="button"
              role="tab"
              aria-selected={selectedTab === tab.id}
              aria-controls={`${tab.id}-panel`}
              tabIndex={selectedTab === tab.id ? 0 : -1}
              onClick={() => selectTab(tab.id)}
              onKeyDown={(event) => selectByKeyboard(event, index)}
            >
              {tab.label}
            </Button>
          ))}
        </div>
      </nav>
    </header>
  );
}
