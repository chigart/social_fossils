import type {
  ChatInsightsResponse,
} from "../api";

export const chatInsights: ChatInsightsResponse = {
  chats: [
    {
      chat_id: 10,
      account_id: 1,
      platform: "telegram",
      source_account_label: "@anton",
      title: "Private group",
      chat_type: "private_group",
      ordinary_message_count: 20,
      average_activity_time: "18:43",
      weekday_activity: [
        { period: "Monday", count: 3 },
        { period: "Tuesday", count: 4 },
        { period: "Wednesday", count: 2 },
        { period: "Thursday", count: 3 },
        { period: "Friday", count: 4 },
        { period: "Saturday", count: 2 },
        { period: "Sunday", count: 2 },
      ],
      month_activity: [
        { period: "January", count: 2 },
        { period: "February", count: 1 },
        { period: "March", count: 3 },
        { period: "April", count: 2 },
        { period: "May", count: 1 },
        { period: "June", count: 2 },
        { period: "July", count: 1 },
        { period: "August", count: 2 },
        { period: "September", count: 1 },
        { period: "October", count: 2 },
        { period: "November", count: 1 },
        { period: "December", count: 2 },
      ],
      text_length: 440,
      popular_words: [{ word: "hello", count: 8 }],
      popular_emojis: [{ emoji: "❤️", count: 5 }],
      senders: [
        {
          sender_id: "user-anton",
          display_name: "Anton",
          message_count: 12,
          average_activity_time: "19:12",
          text_length: 260,
          popular_words: [{ word: "hello", count: 6 }],
          popular_emojis: [{ emoji: "❤️", count: 3 }],
        },
        {
          sender_id: "user-lena",
          display_name: "Lena",
          message_count: 8,
          average_activity_time: "18:00",
          text_length: 180,
          popular_words: [{ word: "thanks", count: 3 }],
          popular_emojis: [{ emoji: "🎉", count: 2 }],
        },
      ],
      reaction_count: 17,
      reaction_emojis: [{ emoji: "👍", count: 11 }],
      reactors: [
        {
          reactor_id: "user-lena",
          display_name: "Lena",
          reaction_count: 6,
          popular_emojis: [
            { emoji: "👍", count: 4 },
            { emoji: "❤️", count: 2 },
          ],
        },
      ],
      reactor_author_pairs: [
        {
          reactor_id: "user-lena",
          reactor_name: "Lena",
          author_id: "user-anton",
          author_name: "Anton",
          observed_reaction_count: 6,
          messages_with_observed_reaction_count: 6,
          author_message_count: 12,
          observed_message_percentage: 50,
        },
      ],
      message_type_breakdown: [
        { category: "Text", count: 20, with_text_count: 20, senders: [] },
        { category: "Unclassified", count: 2, with_text_count: 0, senders: [] },
        {
          category: "Photo",
          count: 3,
          with_text_count: 1,
          senders: [
            {
              sender_id: "user-anton",
              display_name: "Anton",
              count: 2,
            },
            {
              sender_id: "user-lena",
              display_name: "Lena",
              count: 1,
            },
          ],
        },
        {
          category: "Video",
          count: 2,
          with_text_count: 0,
          senders: [
            {
              sender_id: "user-lena",
              display_name: "Lena",
              count: 2,
            },
          ],
        },
      ],
      reply_tempo: {
        reply_reference_count: 7,
        measured_reply_count: 5,
        average_response_seconds: 1800,
        longest_response_seconds: 7200,
        median_response_seconds: 1800,
      },
      conversation_activity: {
        session_gap_hours: 12,
        session_count: 8,
        messages_without_timestamp_count: 1,
        sender_transition_count: 14,
        sender_switch_count: 12,
        sender_switch_percentage: 85.7,
        longest_turn_taking_streak: 6,
        attributed_handoff_count: 3,
        unattributed_handoff_count: 1,
        opening_senders: [
          { sender_id: "user-anton", display_name: "Anton", count: 5 },
          { sender_id: "user-lena", display_name: "Lena", count: 3 },
        ],
        closing_senders: [
          { sender_id: "user-lena", display_name: "Lena", count: 5 },
          { sender_id: "user-anton", display_name: "Anton", count: 3 },
        ],
        handoffs: [
          {
            previous_closer_id: "user-anton",
            previous_closer_name: "Anton",
            next_opener_id: "user-lena",
            next_opener_name: "Lena",
            count: 2,
          },
        ],
      },
    },
  ],
};
