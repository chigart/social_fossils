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
} as const;

export type UploadPlatform = keyof typeof PLATFORM_CONFIG;

const PLATFORM_ACCOUNT_PREFIXES: Record<string, string> = {
  facebook: "FB",
  instagram: "IG",
  telegram: "TG",
  vk: "VK",
};

export function formatPlatformAccountLabel(
  platform: string,
  accountLabel: string,
): string {
  const prefix =
    PLATFORM_ACCOUNT_PREFIXES[platform.toLowerCase()] ??
    platform.slice(0, 2).toUpperCase();
  return `${prefix}${accountLabel.startsWith("@") ? "" : " "}${accountLabel}`;
}

export function platformAccountBadgeClassName(platform: string): string {
  const normalizedPlatform = platform.toLowerCase();
  return `bg-platform-${normalizedPlatform}-background text-platform-${normalizedPlatform}-foreground`;
}
