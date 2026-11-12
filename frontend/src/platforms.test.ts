import { describe, expect, it } from "vitest";
import {
  formatPlatformAccountLabel,
  platformAccountBadgeClassName,
} from "./platforms";

describe("platform account labels", () => {
  it("uses compact usernames and colon-separated named accounts", () => {
    expect(formatPlatformAccountLabel("telegram", "@Anton")).toBe("TG@Anton");
    expect(formatPlatformAccountLabel("vk", "Anton Malkov")).toBe(
      "VK: Anton Malkov",
    );
  });

  it("uses platform colors and a neutral fallback for unknown platforms", () => {
    expect(platformAccountBadgeClassName("telegram")).toBe(
      "bg-platform-telegram-background text-platform-telegram-foreground",
    );
    expect(platformAccountBadgeClassName("instagram")).toBe(
      "bg-platform-instagram-background text-platform-instagram-foreground",
    );
    expect(platformAccountBadgeClassName("facebook")).toBe(
      "bg-platform-facebook-background text-platform-facebook-foreground",
    );
    expect(platformAccountBadgeClassName("vk")).toBe(
      "bg-platform-vk-background text-platform-vk-foreground",
    );
    expect(platformAccountBadgeClassName("unknown")).toBe(
      "bg-surface-neutral text-ink-neutral",
    );
  });
});
