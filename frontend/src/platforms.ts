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

export type UploadPlatform = keyof typeof PLATFORM_CONFIG;

export const PLATFORM_ACCOUNT_PREFIXES: Record<string, string> = {
  facebook: "FB",
  instagram: "IG",
  telegram: "TG",
  vk: "VK",
};

const PLATFORM_ACCOUNT_BADGE_CLASS_NAMES: Record<string, string> = {
  facebook: "bg-platform-facebook-background text-platform-facebook-foreground",
  instagram: "bg-platform-instagram-background text-platform-instagram-foreground",
  telegram: "bg-platform-telegram-background text-platform-telegram-foreground",
  vk: "bg-platform-vk-background text-platform-vk-foreground",
};

export function formatPlatformAccountLabel(
  platform: string,
  accountLabel: string,
): string {
  const prefix = platformAccountPrefix(platform);
  return accountLabel.startsWith("@")
    ? `${prefix}${accountLabel}`
    : `${prefix}: ${accountLabel}`;
}

export function platformAccountPrefix(platform: string): string {
  return (
    PLATFORM_ACCOUNT_PREFIXES[platform.toLowerCase()] ??
    platform.slice(0, 2).toUpperCase()
  );
}

export function platformAccountBadgeClassName(platform: string): string {
  return (
    PLATFORM_ACCOUNT_BADGE_CLASS_NAMES[platform.toLowerCase()] ??
    "bg-surface-neutral text-ink-neutral"
  );
}
