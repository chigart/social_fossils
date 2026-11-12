import {
  formatPlatformAccountLabel,
  platformAccountBadgeClassName,
} from "../platforms";

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
