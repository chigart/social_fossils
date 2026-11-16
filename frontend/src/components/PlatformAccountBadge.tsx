import {
  formatPlatformAccountLabel,
  platformAccountBadgeClassName,
  platformAccountPrefix,
} from "../utils/platforms";

export function PlatformAccountBadge({
  platform,
  accountLabel,
  className = "inline-block whitespace-nowrap rounded px-[7px] py-1 text-label font-semibold",
}: {
  platform: string;
  accountLabel: string;
  className?: string;
}) {
  return (
    <span
      className={`${className} ${platformAccountBadgeClassName(platform)}`}
    >
      {formatPlatformAccountLabel(platform, accountLabel)}
    </span>
  );
}

export function PlatformBadge({ platform }: { platform: string }) {
  return (
    <span
      aria-label={platform}
      className={`inline-flex items-center rounded px-1 py-0.5 text-label font-semibold leading-none ${platformAccountBadgeClassName(platform)}`}
      data-platform-badge
      title={platform}
    >
      {platformAccountPrefix(platform)}
    </span>
  );
}
