import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../format";
import { PERCENTAGE_DECIMAL_PLACES } from "./chatInsightsConstants";
import {
  chatInsightsCardClassName,
  chatInsightsDescriptionClassName,
  chatInsightsEmptyTextClassName,
  chatInsightsGridClassName,
  chatInsightsListClassName,
  chatInsightsListItemClassName,
  chatInsightsParticipantCountClassName,
  chatInsightsPersonNameClassName,
  chatInsightsSectionClassName,
  chatInsightsSectionHeaderClassName,
  chatInsightsSectionTitleClassName,
  chatInsightsSubheadingClassName,
  sectionEyebrowClassName,
} from "../styles";
import { MetricCard } from "./Feedback";
import { formatResponseTime } from "./formatResponseTime";

export function ConversationFlow({ chat }: { chat: ChatInsightsStatistics }) {
  const activity = chat.conversation_activity;
  const replyTempo = chat.reply_tempo;
  const senderGroups = [
    { title: "Conversation openers", senders: activity.opening_senders },
    { title: "Conversation closers", senders: activity.closing_senders },
  ];

  return (
    <section
      className={chatInsightsSectionClassName}
      aria-labelledby="conversation-flow-title"
    >
      <div className={chatInsightsSectionHeaderClassName}>
        <p className={sectionEyebrowClassName}>REPLY TEMPO & TURN-TAKING</p>
        <h3
          id="conversation-flow-title"
          className={chatInsightsSubheadingClassName}
        >
          Conversation flow
        </h3>
      </div>
      <p className={chatInsightsDescriptionClassName}>
        A conversation starts after {activity.session_gap_hours} hours without
        an ordinary message. Reply times include only matched, dated replies
        between identified senders; unknown senders and missing timestamps are
        excluded.
      </p>
      <div className="mb-4 grid grid-cols-4 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
        <MetricCard
          label="Conversations"
          value={formatNumber(activity.session_count)}
          detail={`${formatNumber(activity.messages_without_timestamp_count)} undated messages excluded`}
        />
        <MetricCard
          label="Median reply time"
          value={formatResponseTime(replyTempo.median_response_seconds)}
          detail={`${formatNumber(replyTempo.measured_reply_count)} measured of ${formatNumber(replyTempo.reply_reference_count)} reply references`}
        />
        <MetricCard
          label="Turn-taking"
          value={`${activity.sender_switch_percentage.toFixed(PERCENTAGE_DECIMAL_PLACES)}%`}
          detail={`${formatNumber(activity.sender_switch_count)} sender switches of ${formatNumber(activity.sender_transition_count)} identified transitions`}
        />
        <MetricCard
          label="Longest turn-taking streak"
          value={formatNumber(activity.longest_turn_taking_streak)}
          detail="messages with a sender switch each turn"
        />
      </div>
      <div className={chatInsightsGridClassName}>
        {senderGroups.map(({ title, senders }) => (
          <section className={chatInsightsCardClassName} key={title}>
            <h4 className={chatInsightsSectionTitleClassName}>{title}</h4>
            {senders.length === 0 ? (
              <p className={chatInsightsEmptyTextClassName}>
                No dated conversations available.
              </p>
            ) : (
              <ul className={chatInsightsListClassName}>
                {senders.map((sender) => (
                  <li
                    className={chatInsightsListItemClassName}
                    key={sender.sender_telegram_id ?? "unknown"}
                  >
                    <span className={chatInsightsPersonNameClassName}>
                      {sender.display_name}
                    </span>
                    <span className={chatInsightsParticipantCountClassName}>
                      {formatNumber(sender.count)} conversations
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
      <section
        className={`mt-3 ${chatInsightsCardClassName}`}
        aria-labelledby="conversation-handoffs-title"
      >
        <h4
          id="conversation-handoffs-title"
          className={chatInsightsSectionTitleClassName}
        >
          Who reopens after a pause
        </h4>
        <p className="mb-3 text-caption text-ink-muted">
          Previous conversation closer → next conversation opener ·{" "}
          {formatNumber(activity.unattributed_handoff_count)} transitions have
          an unknown participant.
        </p>
        {activity.handoffs.length === 0 ? (
          <p className={chatInsightsEmptyTextClassName}>
            No fully attributed conversation handoffs available.
          </p>
        ) : (
          <ul className={chatInsightsListClassName}>
            {activity.handoffs.map((handoff) => (
              <li
                className={chatInsightsListItemClassName}
                key={`${handoff.previous_closer_id}:${handoff.next_opener_id}`}
              >
                <span className={chatInsightsPersonNameClassName}>
                  {handoff.previous_closer_name} → {handoff.next_opener_name}
                </span>
                <span className={chatInsightsParticipantCountClassName}>
                  {formatNumber(handoff.count)} times
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
