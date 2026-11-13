import { useMemo } from "react";
import type {
  CommunicationBalanceStatistics,
  ContactStatistics,
  ForgottenContactsStatistics,
  PaginatedItems,
  ChatStatistics,
  SearchOption,
} from "../api";
import type { SearchPickerOption } from "../components/SearchPicker";

type ContactSearchSource = {
  display_name: string | null;
  platforms: string[];
  platform_user_ids: string[];
  source_account_labels: string[];
};

function optionsFromApi(options: SearchOption[]): SearchPickerOption[] {
  return options.map((option) => ({
    value: option.value,
    label: option.label,
    platforms: option.platforms,
    searchTerms: option.search_terms,
  }));
}

function contactSearchOption<T extends ContactSearchSource>(
  contact: T,
  index: number,
  trimName = false,
): SearchPickerOption {
  const displayName = trimName
    ? contact.display_name?.trim()
    : contact.display_name;
  return {
    value: String(index),
    label: displayName || "Unnamed contact",
    platforms: contact.platforms,
    searchTerms: [
      ...contact.platform_user_ids,
      ...contact.source_account_labels,
    ],
  };
}

export function useViewSearchOptions({
  chats,
  contacts,
  balance,
  forgotten,
}: {
  chats: PaginatedItems<ChatStatistics> | null;
  contacts: PaginatedItems<ContactStatistics> | null;
  balance: CommunicationBalanceStatistics | null;
  forgotten: ForgottenContactsStatistics | null;
}) {
  const chatOptions = useMemo(
    () =>
      chats?.options?.length
        ? optionsFromApi(chats.options)
        : (chats?.items ?? []).map((chat) => ({
            value: String(chat.chat_id),
            label: chat.title || "Untitled chat",
            platforms: [chat.platform],
            searchTerms: [
              chat.platform_chat_id,
              chat.chat_type,
              chat.source_account_label,
            ],
          })),
    [chats],
  );
  const contactOptions = useMemo(
    () =>
      contacts?.options?.length
        ? optionsFromApi(contacts.options)
        : (contacts?.items ?? [])
            .map((contact, index) => ({ contact, index }))
            .filter(
              ({ contact }) =>
                contact.display_name?.trim() ||
                contact.platform_user_ids.length > 0,
            )
            .map(({ contact, index }) =>
              contactSearchOption(contact, index, true),
            ),
    [contacts],
  );
  const balanceOptions = useMemo(
    () =>
      balance?.options?.length
        ? optionsFromApi(balance.options)
        : (balance?.contacts ?? []).map((contact, index) =>
            contactSearchOption(contact, index),
          ),
    [balance],
  );
  const forgottenOptions = useMemo(
    () =>
      forgotten?.options?.length
        ? optionsFromApi(forgotten.options)
        : (forgotten?.contacts ?? []).map((contact, index) =>
            contactSearchOption(contact, index),
          ),
    [forgotten],
  );

  return { chatOptions, contactOptions, balanceOptions, forgottenOptions };
}
