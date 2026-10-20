export function DashboardIntro() {
  return (
    <section
      className="flex items-end justify-between gap-7 px-0 pt-2 pb-9 max-sm:block max-sm:pb-[26px]"
      aria-labelledby="page-title"
    >
      <div>
        <p className="mb-[9px] text-label font-bold tracking-[0.13em] text-brand">
          PERSONAL DATA ANALYTICS
        </p>
        <h1
          id="page-title"
          className="mb-2 text-page-title font-bold tracking-[-0.045em] text-ink"
        >
          Your communication, in context.
        </h1>
        <p className="m-0 max-w-[620px] text-body leading-[1.6] text-ink-muted">
          A clear view of the conversations and connections in your Telegram export.
        </p>
      </div>
      <span className="mb-[5px] flex-none rounded-[20px] border border-border-brand bg-surface-green-soft px-[11px] py-2 text-caption font-semibold text-brand-strong max-sm:mt-[14px] max-sm:inline-block">
        Private by design
      </span>
    </section>
  );
}
