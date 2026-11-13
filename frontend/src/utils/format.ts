import { dateFormat, numberFormat } from "../constants";

export function formatNumber(value: number) {
  return numberFormat.format(value);
}

export function formatDate(value: string | null) {
  if (value === null) return "—";

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateFormat.format(date);
}
