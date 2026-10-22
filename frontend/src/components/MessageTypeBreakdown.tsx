import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../format";
import {
  chatInsightsEmptyTextClassName,
  chatInsightsDescriptionClassName,
  chatInsightsSectionClassName,
  chatInsightsSectionHeaderClassName,
  chatInsightsSubheadingClassName,
  chatInsightsTableClassName,
  chatInsightsTableCellClassName,
  chatInsightsTableHeaderCellClassName,
  chatInsightsTableHeaderRowClassName,
  chatInsightsTableLabelCellClassName,
  chatInsightsTableRowClassName,
  sectionEyebrowClassName,
} from "../styles";

export function MessageTypeBreakdown({
  chat,
}: {
  chat: ChatInsightsStatistics;
}) {
  return (
    <section
      className={chatInsightsSectionClassName}
      aria-labelledby="message-type-breakdown-title"
    >
      <div className={chatInsightsSectionHeaderClassName}>
        <p className={sectionEyebrowClassName}>TEXT, MEDIA & EVENTS</p>
        <h3
          id="message-type-breakdown-title"
          className={chatInsightsSubheadingClassName}
        >
          Message type breakdown
        </h3>
      </div>
      <p className={chatInsightsDescriptionClassName}>
        Each exported message is counted once by its primary type. Captions
        remain attached to their media category; service events and unclassified
        messages are shown separately.
      </p>
      {chat.message_type_breakdown.length === 0 ? (
        <p className={chatInsightsEmptyTextClassName}>
          No message type information is available.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border-subtle bg-surface">
          <table className={chatInsightsTableClassName}>
            <thead>
              <tr className={chatInsightsTableHeaderRowClassName}>
                <th className={chatInsightsTableHeaderCellClassName}>
                  Message type
                </th>
                <th className={chatInsightsTableHeaderCellClassName}>
                  Messages
                </th>
                <th className={chatInsightsTableHeaderCellClassName}>
                  With text
                </th>
              </tr>
            </thead>
            <tbody>
              {chat.message_type_breakdown.map((item) => (
                <tr
                  className={chatInsightsTableRowClassName}
                  key={item.category}
                >
                  <th
                    scope="row"
                    className={chatInsightsTableLabelCellClassName}
                  >
                    {item.category}
                  </th>
                  <td className={chatInsightsTableCellClassName}>
                    {formatNumber(item.count)}
                  </td>
                  <td className={chatInsightsTableCellClassName}>
                    {formatNumber(item.with_text_count)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
