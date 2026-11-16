export const DEFAULT_PAGE_SIZE = 50;
export const FRIEND_STATUS_BADGE_CLASS_NAMES = {
  Active: "friend-status-badge--active",
  Close: "friend-status-badge--close",
  exClose: "friend-status-badge--exclose",
} as const;
export const FRIEND_STATUS_BADGE_BASE_CLASS_NAME =
  "inline-block whitespace-nowrap rounded px-[7px] py-1 text-label font-semibold";

export const CYRILLIC_TO_LATIN: Record<string, string> = {
  а: "a",
  б: "b",
  в: "v",
  г: "g",
  д: "d",
  е: "e",
  ё: "e",
  ж: "zh",
  з: "z",
  и: "i",
  й: "y",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "kh",
  ц: "ts",
  ч: "ch",
  ш: "sh",
  щ: "shch",
  ъ: "",
  ы: "y",
  ь: "",
  э: "e",
  ю: "yu",
  я: "ya",
};

export const SECONDS_PER_MINUTE = 60;
export const MINUTES_PER_HOUR = 60;
export const HOURS_PER_DAY = 24;
export const SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR;
export const SECONDS_PER_DAY = SECONDS_PER_HOUR * HOURS_PER_DAY;
export const RESPONSE_TIME_DECIMAL_PLACES = 1;
export const PERCENTAGE_DECIMAL_PLACES = 1;
export const TOP_SENDER_COUNT = 10;
export const TOP_MESSAGE_TYPE_SENDER_COUNT = 5;
export const PERCENTAGE_SCALE = 100;
export const DEGREES_PER_PERCENTAGE_POINT = 3.6;
export const MINIMUM_REPEATED_ITEM_COUNT = 2;
export const MINIMUM_HANDOFF_COUNT = 3;

export const PLATFORM_CONFIG = {
  telegram: {
    label: "Telegram",
    acceptedFileType: ".json,application/json",
    fileInputLabel: "Choose Telegram JSON files",
    instructions: "Choose a Telegram JSON export.",
  },
  instagram: {
    label: "Instagram",
    acceptedFileType: ".zip,application/zip",
    fileInputLabel: "Choose Instagram ZIP files",
    instructions:
      "Choose the downloaded Instagram ZIP archive with JSON selected as its export format.",
  },
  facebook: {
    label: "Facebook",
    acceptedFileType: ".zip,application/zip",
    fileInputLabel: "Choose Facebook ZIP files",
    instructions:
      "Choose the downloaded Facebook ZIP archive with JSON selected as its export format.",
  },
  vk: {
    label: "VK",
    acceptedFileType: ".zip,application/zip",
    fileInputLabel: "Choose VK ZIP files",
    instructions: "Choose the downloaded VK ZIP export with message history.",
  },
} as const;

export const PLATFORM_ACCOUNT_PREFIXES: Record<string, string> = {
  facebook: "FB",
  instagram: "IG",
  telegram: "TG",
  vk: "VK",
};

export const PLATFORM_ACCOUNT_BADGE_CLASS_NAMES: Record<string, string> = {
  facebook: "bg-platform-facebook-background text-platform-facebook-foreground",
  instagram: "bg-platform-instagram-background text-platform-instagram-foreground",
  telegram: "bg-platform-telegram-background text-platform-telegram-foreground",
  vk: "bg-platform-vk-background text-platform-vk-foreground",
};

export const dashboardTabs = [
  { id: "overview", label: "Overview" },
  { id: "contacts", label: "Contacts" },
  { id: "dms", label: "DMs" },
  { id: "chats", label: "Chats" },
  { id: "conversation-insights", label: "Insights" },
  { id: "identity-links", label: "Links" },
  { id: "communication-balance", label: "Balance" },
  { id: "forgotten-contacts", label: "Forgotten" },
  { id: "interactions", label: "Interactions" },
  { id: "uploads", label: "Import" },
  { id: "ai", label: "AI" },
] as const;

export const forgottenClassificationLabels = {
  inactive: "Inactive",
  activity_declined: "Declining",
  active: "Active",
  insufficient_data: "Insufficient data",
} as const;

export const forgottenEvidenceLabels = {
  reliable_baseline: "Reliable baseline",
  insufficient_history: "Insufficient history",
  insufficient_baseline: "Insufficient baseline",
  ambiguous_direction: "Ambiguous direction",
} as const;

export const communicationBalanceClassificationLabels = {
  balanced: "Balanced",
  mostly_owner: "Mostly owner",
  mostly_contact: "Mostly contact",
  strongly_owner: "Strongly owner",
  strongly_contact: "Strongly contact",
  insufficient_data: "Insufficient data",
} as const;

export const communicationBalanceClassifications = Object.keys(
  communicationBalanceClassificationLabels,
) as (keyof typeof communicationBalanceClassificationLabels)[];

export const SEARCH_PICKER_OPTION_LIMIT = 100;
export const MINIMUM_CHART_WIDTH = 620;
export const CHART_HEIGHT = 240;
export const CHART_TOP_PADDING = 16;
export const CHART_BOTTOM_PADDING = 58;
export const Y_AXIS_WIDTH = 46;
export const CHART_RIGHT_PADDING = 18;
export const SLOT_WIDTH = 88;
export const BAR_WIDTH = 36;
export const PLOT_BOTTOM = CHART_HEIGHT - CHART_BOTTOM_PADDING;
export const PLOT_HEIGHT = PLOT_BOTTOM - CHART_TOP_PADDING;

export const actionVariantClassName = {
  positive: "bg-surface-brand",
  danger: "bg-border-warning",
} as const;

export const senderColors = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
  "var(--color-chart-6)",
  "var(--color-chart-7)",
  "var(--color-chart-8)",
  "var(--color-chart-9)",
  "var(--color-chart-10)",
];

export const numberFormat = new Intl.NumberFormat();
export const dateFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
});

export const airflowPollIntervalMs = 3000;

export const sectionClassName =
  "mb-6 scroll-mt-[18px] rounded-xl border border-border bg-surface p-[25px] shadow-[0_2px_7px_var(--color-shadow)] max-sm:mb-[15px] max-sm:px-[14px] max-sm:py-[17px]";
export const sectionHeaderClassName =
  "mb-5 flex min-h-11 items-end justify-between gap-[18px] max-sm:mb-[15px] max-sm:flex-col max-sm:items-start max-sm:gap-3";
export const sectionEyebrowClassName =
  "mb-[5px] text-label font-bold tracking-[0.13em] text-brand";
export const sectionTitleClassName =
  "m-0 text-section-heading font-bold tracking-[-0.035em]";
export const navigationLinkClassName =
  "text-inherit no-underline hover:text-brand-strong focus-visible:rounded-sm focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-3";
export const tableContainerClassName =
  "w-full overflow-x-auto rounded-lg border border-border-subtle";
export const tableClassName = "w-full border-collapse text-left text-small";
export const tableHeadClassName = "bg-surface-muted text-ink-table";
export const tableRowClassName = "hover:bg-surface-subtle";
export const tableRowTitleClassName =
  "min-w-[150px] max-w-[250px] break-words border-b border-border-muted px-[13px] py-3 text-left align-middle font-semibold last:border-b-0";
export const tableCellClassName =
  "border-b border-border-muted px-[13px] py-3 align-middle last:border-b-0";
export const numericTableCellClassName =
  "border-b border-border-muted px-[13px] py-3 text-left align-middle tabular-nums whitespace-nowrap last:border-b-0";
export const searchLabelClassName = "w-[min(270px,38vw)] max-sm:w-full";
export const searchInputClassName =
  "min-h-[38px] w-full rounded-[7px] border border-border-input bg-surface px-3 py-2 text-small text-ink outline-none placeholder:text-ink-placeholder focus:border-brand focus:ring-[3px] focus:ring-focus-ring";
export const emptyStateClassName =
  "rounded-lg border border-border-brand bg-surface-green text-center text-ink-green";
export const emptyStateTextClassName =
  "m-0 text-small leading-[1.5] text-ink-green-muted";
export const emptyStateTitleClassName = "mb-[7px] text-subheading text-ink";
export const screenReaderOnlyClassName = "sr-only";
export const tableHeaderClassName =
  "whitespace-nowrap px-[13px] py-3 text-label font-bold";
export const chatInsightsCardClassName =
  "rounded-lg border border-border-subtle bg-surface p-4";
export const chatInsightsEmptyTextClassName = "m-0 text-small text-ink-muted";
export const chatInsightsGridClassName =
  "grid grid-cols-2 gap-3 max-[820px]:grid-cols-1";
export const chatInsightsListClassName = "m-0 list-none space-y-2 p-0";
export const chatInsightsListItemClassName =
  "flex justify-between gap-3 text-small";
export const chatInsightsTableClassName =
  "w-full border-collapse text-left text-small";
export const chatInsightsTableHeaderRowClassName =
  "border-b border-border-subtle text-caption text-ink-muted";
export const chatInsightsTableRowClassName =
  "border-b border-border-subtle last:border-b-0";
export const chatInsightsTableHeaderCellClassName =
  "px-4 py-2 font-semibold";
export const chatInsightsTableCellClassName = "px-4 py-2 text-ink";
export const chatInsightsTableLabelCellClassName =
  "px-4 py-2 font-medium text-ink";
export const chatInsightsCompactHeaderCellClassName =
  "py-2 pr-3 font-semibold";
export const chatInsightsCompactHeaderCellLastClassName =
  "py-2 font-semibold";
export const chatInsightsCompactCellClassName = "py-2 pr-3 text-ink";
export const chatInsightsCompactCellLastClassName = "py-2 text-ink";
export const chatInsightsSectionTitleClassName =
  "mb-3 text-ui font-semibold text-ink";
export const chatInsightsSubheadingClassName =
  "m-0 text-subheading font-bold text-ink";
export const chatInsightsSectionClassName = "mt-6";
export const chatInsightsSectionHeaderClassName = "mb-3";
export const chatInsightsTableWrapperClassName = "overflow-x-auto";
export const chatInsightsDescriptionClassName =
  "mb-4 text-small leading-[1.5] text-ink-muted";
export const chatInsightsPersonNameClassName = "truncate text-ink";
export const chatInsightsParticipantCountClassName = "shrink-0 text-ink-muted";
