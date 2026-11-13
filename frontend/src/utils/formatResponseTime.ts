import {
  RESPONSE_TIME_DECIMAL_PLACES,
  SECONDS_PER_DAY,
  SECONDS_PER_HOUR,
  SECONDS_PER_MINUTE,
} from "../constants";

export function formatResponseTime(seconds: number | null) {
  if (seconds === null) return "Not available";
  if (seconds < SECONDS_PER_MINUTE) return `${Math.round(seconds)} sec`;
  if (seconds < SECONDS_PER_HOUR) {
    return `${Math.round(seconds / SECONDS_PER_MINUTE)} min`;
  }
  if (seconds < SECONDS_PER_DAY) {
    return `${(seconds / SECONDS_PER_HOUR).toFixed(RESPONSE_TIME_DECIMAL_PLACES)} hr`;
  }
  return `${(seconds / SECONDS_PER_DAY).toFixed(RESPONSE_TIME_DECIMAL_PLACES)} days`;
}
