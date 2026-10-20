const numberFormat = new Intl.NumberFormat();
const dateFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatNumber(value: number) {
  return numberFormat.format(value);
}

export function formatDate(value: string | null) {
  if (value === null) return "—";

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateFormat.format(date);
}
