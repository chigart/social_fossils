import { DEFAULT_PAGE_SIZE } from "../constants";
import {
  balance,
  chatInsights,
  chats,
  contacts,
  closeFriendsTimeline,
  ownerReplyTimeline,
  forgotten,
  overview,
  timeline,
} from "./App.testFixtures";

type MockFunction = {
  mockReset: () => unknown;
  mockResolvedValue: (value: unknown) => unknown;
};

export function paginated<T>(items: T[]) {
  return {
    items,
    pagination: {
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
      total: items.length,
    },
    options: [],
  };
}

export function resetDashboardApi(api: Record<string, MockFunction>) {
  Object.values(api).forEach((mock) => mock.mockReset());
  api.getOverview.mockResolvedValue(overview);
  api.getChatInsights.mockResolvedValue(chatInsights);
  api.getChats.mockResolvedValue(paginated(chats));
  api.getContacts.mockResolvedValue(paginated(contacts));
  api.getIdentityLinks.mockResolvedValue({
    identities: [],
    contacts_without_identity: [],
    events: [],
  });
  api.linkPlatformIdentities.mockResolvedValue({
    status: "linked",
    identity_group_id: 1,
  });
  api.unlinkPlatformIdentity.mockResolvedValue({
    status: "unlinked",
    identity_group_id: null,
  });
  api.getCommunicationBalance.mockResolvedValue(balance);
  api.getForgottenContacts.mockResolvedValue(forgotten);
  api.getCommunicationTimeline.mockResolvedValue(timeline);
  api.getCloseFriendsTimeline.mockResolvedValue(closeFriendsTimeline);
  api.getOwnerReplyTimeline.mockResolvedValue(ownerReplyTimeline);
}
