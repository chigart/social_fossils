import {
  PLATFORM_ACCOUNT_BADGE_CLASS_NAMES,
  PLATFORM_ACCOUNT_PREFIXES,
  PLATFORM_CONFIG,
} from "../constants";

export type UploadPlatform = keyof typeof PLATFORM_CONFIG;

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
