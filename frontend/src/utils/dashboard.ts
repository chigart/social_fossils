export function pageForSearchOption(
  value: string,
  options: { value: string }[] | undefined,
  pageSize: number | undefined,
): number {
  if (!value || !options || !pageSize) return 1;
  const index = options.findIndex((option) => option.value === value);
  return index < 0 ? 1 : Math.floor(index / pageSize) + 1;
}
