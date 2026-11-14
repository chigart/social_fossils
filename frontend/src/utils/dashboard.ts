export function pageForSearchOption(
  value: string,
  options: { value: string; platforms?: string[] }[] | undefined,
  pageSize: number | undefined,
  platform?: string,
  valueIsIndex = false,
): number {
  if (!value || !options || !pageSize) return 1;
  const matchingOptions = platform
    ? options.filter((option) => option.platforms?.includes(platform))
    : options;
  const parsedValue = Number(value);
  const index = !platform && valueIsIndex && Number.isInteger(parsedValue)
    ? parsedValue
    : matchingOptions.findIndex((option) => option.value === value);
  return index < 0 ? 1 : Math.floor(index / pageSize) + 1;
}
