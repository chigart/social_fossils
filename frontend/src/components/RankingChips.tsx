import type { EmojiFrequency, WordFrequency } from "../api";
import { formatNumber } from "../utils/format";

export function RankingChips<T extends WordFrequency | EmojiFrequency>({
  items,
  getLabel,
  countLabel,
  labelClassName = "",
  countClassName = "",
}: {
  items: T[];
  getLabel: (item: T) => string;
  countLabel: string;
  labelClassName?: string;
  countClassName?: string;
}) {
  return (
    <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
      {items.map((item) => {
        const label = getLabel(item);
        return (
          <li
            className="inline-flex items-baseline gap-1.5 whitespace-nowrap rounded bg-surface-muted px-2 py-1"
            key={label}
            aria-label={`${label}, ${formatNumber(item.count)} ${countLabel}`}
          >
            <span className={labelClassName}>{label}</span>
            <span className={countClassName}>{formatNumber(item.count)}</span>
          </li>
        );
      })}
    </ul>
  );
}
