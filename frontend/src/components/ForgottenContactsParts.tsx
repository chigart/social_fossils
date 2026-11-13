import type {
  ForgottenContact,
  ForgottenContactsStatistics,
} from "../api";
import {
  forgottenClassificationLabels,
  forgottenEvidenceLabels,
} from "../constants";
import { formatNumber } from "../utils/format";
import { MetricCard } from "./Feedback";

export function ForgottenStatusBadge({
  status,
}: {
  status: ForgottenContact["classification"];
}) {
  const className =
    status === "active"
      ? "border border-border-brand bg-surface-green text-ink-green"
      : status === "activity_declined"
        ? "border border-border-warning bg-surface-warning text-ink-warning"
        : status === "inactive"
          ? "border border-border-subtle bg-surface-muted text-ink"
          : "border border-border-input bg-surface-neutral text-ink-neutral";

  return (
    <span
      className={`inline-block whitespace-nowrap rounded px-[7px] py-1 text-label font-semibold ${className}`}
    >
      {forgottenClassificationLabels[status]}
    </span>
  );
}

export function ForgottenEvidenceBadge({
  status,
}: {
  status: ForgottenContact["evidence_status"];
}) {
  return (
    <span className="inline-block whitespace-nowrap rounded border border-border-input bg-surface-neutral px-[7px] py-1 text-label font-semibold text-ink-neutral">
      {forgottenEvidenceLabels[status]}
    </span>
  );
}

export function ForgottenTrend({
  contact,
}: {
  contact: ForgottenContact;
}) {
  if (contact.activity_decline_percentage === null) {
    return <span className="text-ink-muted">—</span>;
  }

  return (
    <span className="tabular-nums">
      {formatNumber(Math.round(contact.activity_decline_percentage))}%
    </span>
  );
}

export function ForgottenMonthlyActivity({
  label,
  months,
}: {
  label: string;
  months: ForgottenContact["historical_activity_by_month"];
}) {
  const visibleMonths = months.slice(-6);
  const maxCount = Math.max(
    ...visibleMonths.map((month) => month.total_message_count),
    1,
  );

  if (visibleMonths.length === 0) {
    return (
      <p className="m-0 text-caption text-ink-muted">
        {label}: no dated activity
      </p>
    );
  }

  const description = visibleMonths
    .map((month) => `${month.month}: ${month.total_message_count} messages`)
    .join(", ");

  return (
    <div
      className="mb-2 last:mb-0"
      role="img"
      aria-label={`${label} monthly activity: ${description}`}
    >
      <p className="mb-1 m-0 text-caption font-semibold text-ink-muted">
        {label}
      </p>
      <div className="flex min-w-[250px] items-end gap-1">
        {visibleMonths.map((month) => (
          <div
            className="flex min-w-0 flex-1 flex-col items-center gap-1"
            key={month.month}
          >
            <span className="text-caption tabular-nums text-ink-muted">
              {formatNumber(month.total_message_count)}
            </span>
            <span
              className="w-full rounded-t bg-brand"
              style={{
                height: `${Math.max(4, (month.total_message_count / maxCount) * 28)}px`,
              }}
            />
            <span className="text-[10px] text-ink-muted">{month.month}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ForgottenSummaryCards({
  data,
  scope,
}: {
  data: ForgottenContactsStatistics;
  scope: "private" | "group";
}) {
  const { summary } = data;
  return (
    <div className="mb-5 grid grid-cols-5 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
      <MetricCard
        label={scope === "group" ? "Eligible participants" : "Eligible contacts"}
        value={formatNumber(summary.eligible_contacts)}
      />
      <MetricCard
        label="Meaningful history"
        value={formatNumber(summary.meaningful_historical_contacts)}
      />
      <MetricCard
        label="Inactive"
        value={formatNumber(summary.currently_inactive_contacts)}
      />
      <MetricCard
        label="Declining"
        value={formatNumber(summary.declining_activity_contacts)}
      />
      <MetricCard
        label="Insufficient data"
        value={formatNumber(summary.insufficient_data_contacts)}
      />
    </div>
  );
}
