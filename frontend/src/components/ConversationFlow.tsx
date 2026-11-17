import type { ChatInsightsStatistics } from "../api";
import { formatNumber } from "../utils/format";
import {
  MINIMUM_HANDOFF_COUNT,
  PERCENTAGE_DECIMAL_PLACES,
} from "../constants";
import {
  chatInsightsCardClassName,
  chatInsightsDescriptionClassName,
  chatInsightsListClassName,
  chatInsightsListItemClassName,
  chatInsightsParticipantCountClassName,
  chatInsightsPersonNameClassName,
  chatInsightsSectionClassName,
  chatInsightsSectionHeaderClassName,
  chatInsightsSectionTitleClassName,
  chatInsightsSubheadingClassName,
  sectionEyebrowClassName,
} from "../constants";
import { MetricCard } from "./Feedback";
import { formatResponseTime } from "../utils/formatResponseTime";

export function ConversationFlow({ chat }: { chat: ChatInsightsStatistics }) {
  const activity = chat.conversation_activity;
  const replyTempo = chat.reply_tempo;
  const qualifyingHandoffs = activity.handoffs.filter(
    (handoff) => handoff.count >= MINIMUM_HANDOFF_COUNT,
  );
  const senderGroups = [
    {
      title: "Conversation openers",
      senders: activity.opening_senders.filter(
        (sender) => sender.count >= MINIMUM_HANDOFF_COUNT,
      ),
    },
    {
      title: "Conversation closers",
      senders: activity.closing_senders.filter(
        (sender) => sender.count >= MINIMUM_HANDOFF_COUNT,
      ),
    },
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
        an ordinary message. Median message interval measures time between
        consecutive messages within a conversation.
      </p>
      <div className="mb-4 grid grid-cols-4 gap-3 max-[820px]:grid-cols-2 max-sm:gap-2">
        <MetricCard
          label="Conversations"
          value={formatNumber(activity.session_count)}
          detail={`${formatNumber(activity.messages_without_timestamp_count)} undated messages excluded`}
        />
        <MetricCard
          label="Median time between messages"
          value={formatResponseTime(replyTempo.median_message_interval_seconds)}
          detail={`${formatNumber(replyTempo.message_interval_count)} consecutive message intervals`}
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
      <div className="grid grid-cols-2 items-start gap-3 max-sm:grid-cols-1">
        <div className="flex flex-col gap-3">
          {senderGroups.map(
            ({ title, senders }) =>
              senders.length > 0 && (
                <section className={chatInsightsCardClassName} key={title}>
                  <h4 className={chatInsightsSectionTitleClassName}>{title}</h4>
                  <ul className={chatInsightsListClassName}>
                    {senders.map((sender) => (
                      <li
                        className={chatInsightsListItemClassName}
                        key={sender.sender_id ?? "unknown"}
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
                </section>
              ),
          )}
        </div>
        {qualifyingHandoffs.length > 0 && (
          <section
            className={`${chatInsightsCardClassName} max-sm:col-start-1`}
            aria-labelledby="conversation-handoffs-title"
          >
            <h4
              id="conversation-handoffs-title"
              className={chatInsightsSectionTitleClassName}
            >
              Who reopens after a pause
            </h4>
            <p className="mb-3 text-caption text-ink-muted">
              Previous conversation closer → next conversation opener
            </p>
            <ul className={chatInsightsListClassName}>
              {qualifyingHandoffs.map((handoff) => (
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
          </section>
        )}
      </div>
    </section>
  );
}
