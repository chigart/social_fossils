import type { CommunicationBalanceStatistics } from "../api";
import { formatNumber } from "../utils/format";
import { MetricCard } from "./Feedback";

export function CommunicationBalanceSummary({
  data,
}: {
  data: CommunicationBalanceStatistics;
}) {
  const { summary } = data;
  return (
    <div className="mb-5 grid grid-cols-4 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
      <MetricCard label="Eligible contacts" value={formatNumber(summary.eligible_contacts)} />
      <MetricCard label="Balanced" value={formatNumber(summary.balanced_contacts)} />
      <MetricCard label="Mostly owner" value={formatNumber(summary.mostly_owner_contacts)} />
      <MetricCard label="Mostly contact" value={formatNumber(summary.mostly_contact_contacts)} />
      <MetricCard label="Strongly owner" value={formatNumber(summary.strongly_owner_contacts)} />
      <MetricCard label="Strongly contact" value={formatNumber(summary.strongly_contact_contacts)} />
      <MetricCard
        label="Insufficient data"
        value={formatNumber(summary.insufficient_data_contacts)}
      />
      <MetricCard
        label="Total text exchanged"
        value={formatNumber(summary.total_text_length)}
        detail="characters"
      />
    </div>
  );
}
