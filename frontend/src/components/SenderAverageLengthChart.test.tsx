import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { chatInsights } from "../App.testFixtures";
import { SenderAverageLengthChart } from "./SenderAverageLengthChart";

describe("SenderAverageLengthChart", () => {
  it("wraps multi-word sender names onto two lines", () => {
    const senders = [
      {
        ...chatInsights.chats[0].senders[0],
        display_name: "Avery Smith",
      },
    ];

    render(<SenderAverageLengthChart senders={senders} />);

    const chart = screen.getByRole("img", {
      name: "Average message length by person",
    });
    const nameLabel = chart.querySelector(
      'text[data-sender-name="Avery Smith"]',
    );

    expect(
      Array.from(nameLabel?.querySelectorAll("tspan") ?? []).map(
        (line) => line.textContent,
      ),
    ).toEqual(["Avery", "Smith"]);
  });

  it("shows the full sender name across two lines when it is long", () => {
    const fullName = "Avery Long Sender Display Name";
    const senders = [
      {
        ...chatInsights.chats[0].senders[0],
        display_name: fullName,
      },
    ];

    render(<SenderAverageLengthChart senders={senders} />);

    const chart = screen.getByRole("img", {
      name: "Average message length by person",
    });
    const nameLabel = chart.querySelector(
      `text[data-sender-name="${fullName}"]`,
    );
    const lines = Array.from(nameLabel?.querySelectorAll("tspan") ?? []);

    expect(lines).toHaveLength(2);
    expect(
      lines
        .map((line) => line.textContent)
        .join(" "),
    ).toBe(fullName);
  });
});
