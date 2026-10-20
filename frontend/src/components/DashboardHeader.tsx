import { navigationLinkClassName } from "../styles";

export function DashboardHeader() {
  return (
    <header className="flex min-h-[70px] items-center justify-between border-b border-border bg-surface px-[max(28px,calc((100vw-1200px)/2))] max-sm:min-h-[62px] max-sm:px-4">
      <a
        className="inline-flex items-center gap-2.5 font-sans text-logo font-extrabold text-ink no-underline max-sm:gap-[7px] max-sm:text-subheading"
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
        className="flex items-center gap-[30px] text-ui font-semibold text-ink-subtle max-sm:gap-2 max-sm:text-caption max-[360px]:gap-[5px] max-[360px]:text-[10px]"
        aria-label="Dashboard sections"
      >
        <a className={navigationLinkClassName} href="#overview">Overview</a>
        <a className={navigationLinkClassName} href="#chats">Chats</a>
        <a className={navigationLinkClassName} href="#contacts">Contacts</a>
        <a className={navigationLinkClassName} href="#communication-balance">
          Balance
        </a>
      </nav>
    </header>
  );
}
