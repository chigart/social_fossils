import { describe, expect, it } from "vitest";
import { formatDate, formatNumber } from "./format";

describe("formatNumber", () => {
  it("formats values using the runtime locale", () => {
    expect(formatNumber(1234567)).toBe(new Intl.NumberFormat().format(1234567));
  });
});

describe("formatDate", () => {
  it("formats valid timestamps using the runtime locale", () => {
    const timestamp = "2024-03-15T12:30:00.000Z";
    const expected = new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(timestamp));

    expect(formatDate(timestamp)).toBe(expected);
  });

  it("uses an em dash when a timestamp is absent or invalid", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("not-a-date")).toBe("—");
  });
});
