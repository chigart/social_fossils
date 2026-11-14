import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { timeline } from "./App.testFixtures";
import type { Resource } from "../types";
import { CommunicationTimelineView } from "../components/CommunicationTimelineView";

function renderTimeline(
  resource: Resource<typeof timeline> = {
    data: timeline,
    error: null,
    loading: false,
  },
  period: "month" | "year" = "month",
) {
  const onRetry = vi.fn();
  render(
    <CommunicationTimelineView
      timeline={resource}
      onRetry={onRetry}
      senders={[]}
      selectedSenderId={null}
      onSenderChange={vi.fn()}
      showSenderSelector={false}
      period={period}
    />,
  );
  return { onRetry };
}

describe("CommunicationTimelineView", () => {
  it("exposes month totals, gaps, active days, and direction uncertainty", () => {
    renderTimeline();

    const chart = screen.getByRole("img", {
      name: "Monthly ordinary message activity",
    });
    expect(chart.querySelector('[data-month="2023-02"][data-count="0"]')).toBeTruthy();
    expect(chart.querySelector('[data-month="2023-04"][data-count="7"]')).toBeTruthy();
    expect(
      screen.getByRole("list", {
        name: "Monthly communication activity details",
      }),
    ).toHaveTextContent("2023");
    expect(screen.getAllByText("Unknown direction").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Gaps, quieter periods, and renewed activity/),
    ).toBeInTheDocument();
  });

  it("shows separate direction series only when at least one is reliable", () => {
    const unknownOnly = {
      ...timeline,
      summary: {
        ...timeline.summary,
        owner_message_count: 0,
        contact_message_count: 0,
        unknown_direction_message_count: 13,
      },
      months: timeline.months.map((month) => ({
        ...month,
        owner_message_count: 0,
        contact_message_count: 0,
        unknown_direction_message_count: month.ordinary_message_count,
      })),
    };
    renderTimeline({ data: unknownOnly, error: null, loading: false });

    expect(screen.getAllByText("Unknown direction").length).toBeGreaterThan(0);
    expect(screen.queryByText("Owner", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("Contact", { exact: true })).not.toBeInTheDocument();
  });

  it("colors the direction legend swatches with their theme colors", () => {
    renderTimeline();

    const expectedSwatchColors = [
      ["Owner", "bg-brand-strong"],
      ["Contact", "bg-timeline-contact"],
      ["Unknown direction", "bg-timeline-unknown"],
    ];
    for (const [label, colorClass] of expectedSwatchColors) {
      const labelElement = screen.getByText(label, {
        exact: true,
        selector: "span.inline-flex",
      });
      const swatch = labelElement.querySelector('[aria-hidden="true"]');
      expect(swatch).toHaveClass(colorClass);
    }

    const chart = screen.getByRole("img", {
      name: "Monthly ordinary message activity",
    });
    const firstBar = chart.querySelector("rect[data-month='2023-01']");
    expect(Number(firstBar?.getAttribute("x"))).toBeGreaterThan(48);
    expect(chart.querySelector('[fill="var(--color-brand-strong)"]')).toBeTruthy();
    expect(
      chart.querySelector('[fill="var(--color-timeline-contact)"]'),
    ).toBeTruthy();
  });

  it("shows annual message counts and relative average message size", () => {
    const laterYear = {
      ...timeline.months[0],
      month: "2024-01",
      ordinary_message_count: 2,
      text_length: 20,
    };
    renderTimeline(
      {
        data: {
          ...timeline,
          summary: { ...timeline.summary, scope: "owner" },
          months: [...timeline.months, laterYear],
        },
        error: null,
        loading: false,
      },
      "year",
    );

    expect(
      screen.getByRole("img", {
        name: "Yearly total and owner messages, with owner average message size",
      })
        .querySelector('[data-month="2023"][data-count="13"]'),
    ).toBeTruthy();
    expect(
      screen.getByRole("img", {
        name: "Yearly total and owner messages, with owner average message size",
      }).querySelector('[data-year="2023"][data-year-total-count="13"]'),
    ).toBeTruthy();
    expect(
      screen.getByRole("img", {
        name: "Yearly total and owner messages, with owner average message size",
      }).querySelector('[data-year="2023"][data-year-owner-count="5"]'),
    ).toBeTruthy();
    expect(
      screen.getByRole("img", {
        name: "Yearly total and owner messages, with owner average message size",
      }).querySelector('[data-year="2023"][data-average-size]'),
    ).toBeTruthy();
    const yearlyChart = screen.getByRole("img", {
      name: "Yearly total and owner messages, with owner average message size",
    });
    const higherAverageMarker = yearlyChart.querySelector(
      '[data-year="2023"][data-average-size]',
    );
    const lowerAverageMarker = yearlyChart.querySelector(
      '[data-year="2024"][data-average-size]',
    );
    expect(higherAverageMarker?.getAttribute("data-average-size")).toBe("6.4");
    expect(Number(higherAverageMarker?.getAttribute("cy"))).toBe(15);
    expect(
      Number(lowerAverageMarker?.getAttribute("cy")),
    ).toBeGreaterThan(Number(higherAverageMarker?.getAttribute("cy")));
    expect(Number(lowerAverageMarker?.getAttribute("cy"))).toBeCloseTo(76.875);
    expect(
      yearlyChart.querySelector('[data-series="average-message-size"]'),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: "Yearly text volume in characters" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("list", {
        name: "Yearly communication activity details",
      }),
    ).toHaveTextContent(
      "2023: 13 ordinary messages total, 5 from owner, 32 owner characters",
    );
    expect(
      screen.getByText(
        "Owner average message size (characters; highest year at top)",
      ),
    ).toBeInTheDocument();
  });

  it("reports loading and error states and calls retry", () => {
    const loading = renderTimeline({ data: null, error: null, loading: true });
    expect(screen.getByRole("status")).toHaveTextContent("Loading analytics");

    loading.onRetry.mockReset();
    const failed = renderTimeline({
      data: null,
      error: "Timeline unavailable.",
      loading: false,
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Timeline unavailable.");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(failed.onRetry).toHaveBeenCalledOnce();
  });

  it("explains when all ordinary messages are undated", () => {
    renderTimeline({
      data: {
        ...timeline,
        summary: {
          ...timeline.summary,
          ordinary_message_count: 2,
          dated_ordinary_message_count: 0,
          undated_ordinary_message_count: 2,
        },
        months: [],
      },
      error: null,
      loading: false,
    });

    expect(
      screen.getByRole("heading", { name: "No dated ordinary messages" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/2 ordinary messages have no reliable timestamp/),
    ).toBeInTheDocument();
  });
});
