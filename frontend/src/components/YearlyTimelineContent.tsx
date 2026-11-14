import type { CommunicationTimelineMonth } from "../api";
import { screenReaderOnlyClassName } from "../constants";
import { formatNumber } from "../utils/format";
import { TimelineChart } from "./TimelineChart";

export function YearlyTimelineContent({
  months,
}: {
  months: CommunicationTimelineMonth[];
}) {
  const years = months.reduce<
    Map<
      string,
      {
        totalMessageCount: number;
        ownerMessageCount: number;
        ownerTextLength: number;
      }
    >
  >((totals, month) => {
    const year = month.month.slice(0, 4);
    const total = totals.get(year) ?? {
      totalMessageCount: 0,
      ownerMessageCount: 0,
      ownerTextLength: 0,
    };
    total.totalMessageCount += month.ordinary_message_count;
    total.ownerMessageCount += month.owner_message_count;
    total.ownerTextLength += month.owner_text_length;
    totals.set(year, total);
    return totals;
  }, new Map());
  const yearlyPoints = [...years].map(([label, total]) => ({
    label,
    count: total.totalMessageCount,
    ownerCount: total.ownerMessageCount,
    lineValue: total.ownerMessageCount
      ? total.ownerTextLength / total.ownerMessageCount
      : undefined,
  }));

  return (
    <>
      <h3 className="mb-2 text-small font-bold text-ink">
        Total and owner messages per year
      </h3>
      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-2 text-caption text-ink-muted">
        <span className="inline-flex items-center gap-2">
          <span
            className="size-2.5 rounded-sm bg-timeline-contact"
            aria-hidden="true"
          />
          Total messages
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            className="size-2.5 rounded-sm bg-brand-strong"
            aria-hidden="true"
          />
          Owner messages
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            className="h-0 w-4 border-t-[2.5px] border-timeline-contact"
            aria-hidden="true"
          />
          Owner average message size (characters; highest year at top)
        </span>
      </div>
      <TimelineChart
        points={yearlyPoints}
        showDirection={false}
        title="Yearly total and owner messages, with owner average message size"
        description="Paired bars compare all dated ordinary messages with the subset sent by the owner. The connected line shows average text characters per dated ordinary message sent by the owner. The year with the largest average owner message size is at the top of the chart."
        chartId="yearly-message-timeline"
        compareOwnerCount
        lineLegendLabel="Relative average owner message size"
      />
      <ul
        className={screenReaderOnlyClassName}
        aria-label="Yearly communication activity details"
      >
        {[...years].map(([year, total]) => (
          <li key={year}>
            {year}: {formatNumber(total.totalMessageCount)} ordinary messages
            total, {formatNumber(total.ownerMessageCount)} from owner,{" "}
            {formatNumber(total.ownerTextLength)} owner characters
          </li>
        ))}
      </ul>
    </>
  );
}
