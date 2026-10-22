import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../format";
import {
  chatInsightsCardClassName,
  chatInsightsCompactCellClassName,
  chatInsightsCompactCellLastClassName,
  chatInsightsCompactHeaderCellClassName,
  chatInsightsCompactHeaderCellLastClassName,
  chatInsightsEmptyTextClassName,
  chatInsightsTableClassName,
  chatInsightsTableHeaderRowClassName,
  chatInsightsTableRowClassName,
  chatInsightsSectionClassName,
  chatInsightsSectionHeaderClassName,
  chatInsightsSectionTitleClassName,
  chatInsightsSubheadingClassName,
  chatInsightsTableWrapperClassName,
  sectionEyebrowClassName,
} from "../styles";
import { PERCENTAGE_DECIMAL_PLACES } from "./chatInsightsConstants";
import { RankingChips } from "./RankingChips";

export function ReactionAnalytics({ chat }: { chat: ChatInsightsStatistics }) {
  return (
    <section
      className={chatInsightsSectionClassName}
      aria-labelledby="reaction-analytics-title"
    >
      <div className={chatInsightsSectionHeaderClassName}>
        <p className={sectionEyebrowClassName}>REACTIONS</p>
        <h3
          id="reaction-analytics-title"
          className={chatInsightsSubheadingClassName}
        >
          Reaction patterns
        </h3>
      </div>
      <p className="mb-4 rounded-lg border border-border-brand bg-surface-green px-4 py-3 text-small leading-[1.5] text-ink-green">
        Chat-wide emoji totals use the full reaction counts in the export.
        Per-person counts and reactor-to-author percentages use Telegram’s
        “recent” reactor lists only, so they show observed coverage and are
        lower bounds when those lists are incomplete.
      </p>
      <section className={chatInsightsCardClassName}>
        <h4 className={chatInsightsSectionTitleClassName}>
          Most popular reactions · {formatNumber(chat.reaction_count)} total
        </h4>
        {chat.reaction_emojis.length > 0 ? (
          <RankingChips
            items={chat.reaction_emojis}
            getLabel={(item) => item.emoji}
            countLabel="reactions"
          />
        ) : (
          <p className={chatInsightsEmptyTextClassName}>
            No exported emoji reactions in this chat.
          </p>
        )}
      </section>
      <div className="mt-3 grid grid-cols-2 gap-3 max-[820px]:grid-cols-1">
        <section className={chatInsightsCardClassName}>
          <h4 className={chatInsightsSectionTitleClassName}>
            Observed reactions by person
          </h4>
          {chat.reactors.length === 0 ? (
            <p className={chatInsightsEmptyTextClassName}>
              No identified reactors in the exported recent lists.
            </p>
          ) : (
            <div className={chatInsightsTableWrapperClassName}>
              <table className={chatInsightsTableClassName}>
                <thead>
                  <tr className={chatInsightsTableHeaderRowClassName}>
                    <th className={chatInsightsCompactHeaderCellClassName}>
                      Person
                    </th>
                    <th className={chatInsightsCompactHeaderCellClassName}>
                      Observed reactions
                    </th>
                    <th className={chatInsightsCompactHeaderCellLastClassName}>
                      Top reactions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {chat.reactors.map((reactor) => (
                    <tr
                      className={chatInsightsTableRowClassName}
                      key={reactor.reactor_telegram_id}
                    >
                      <td className={chatInsightsCompactCellClassName}>
                        {reactor.display_name}
                      </td>
                      <td className={chatInsightsCompactCellClassName}>
                        {formatNumber(reactor.reaction_count)}
                      </td>
                      <td className={chatInsightsCompactCellLastClassName}>
                        {reactor.popular_emojis.length > 0 ? (
                          <RankingChips
                            items={reactor.popular_emojis}
                            getLabel={(item) => item.emoji}
                            countLabel="observed reactions"
                          />
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <section className={chatInsightsCardClassName}>
          <h4 className={chatInsightsSectionTitleClassName}>
            Who reacts to whose messages
          </h4>
          {chat.reactor_author_pairs.length === 0 ? (
            <p className={chatInsightsEmptyTextClassName}>
              No identified reactor-to-author pairs in the exported recent lists.
            </p>
          ) : (
            <div className={chatInsightsTableWrapperClassName}>
              <table className={chatInsightsTableClassName}>
                <thead>
                  <tr className={chatInsightsTableHeaderRowClassName}>
                    <th className={chatInsightsCompactHeaderCellClassName}>
                      Reactor → author
                    </th>
                    <th className={chatInsightsCompactHeaderCellClassName}>
                      Messages observed
                    </th>
                    <th className={chatInsightsCompactHeaderCellLastClassName}>
                      Observed share
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {chat.reactor_author_pairs.map((pair) => (
                    <tr
                      className={chatInsightsTableRowClassName}
                      key={`${pair.reactor_telegram_id}:${pair.author_telegram_id}`}
                    >
                      <td className={chatInsightsCompactCellClassName}>
                        {pair.reactor_name} → {pair.author_name}
                      </td>
                      <td className={chatInsightsCompactCellClassName}>
                        {formatNumber(
                          pair.messages_with_observed_reaction_count,
                        )}{" "}
                        /{" "}
                        {formatNumber(pair.author_message_count)}
                      </td>
                      <td className={chatInsightsCompactCellLastClassName}>
                        {pair.observed_message_percentage.toFixed(
                          PERCENTAGE_DECIMAL_PLACES,
                        )}
                        %
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
