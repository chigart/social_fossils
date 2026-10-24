import {
  formatPlatformAccountLabel,
  platformAccountBadgeClassName,
} from "../platforms";

export function PlatformAccountBadge({
  platform,
  accountLabel,
}: {
  platform: string;
  accountLabel: string;
}) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded px-[7px] py-1 text-label font-semibold ${platformAccountBadgeClassName(platform)}`}
    >
      {formatPlatformAccountLabel(platform, accountLabel)}
    </span>
  );
}
