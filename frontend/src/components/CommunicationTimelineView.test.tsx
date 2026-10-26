import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { timeline } from "../App.testFixtures";
import type { Resource } from "../types";
import { CommunicationTimelineView } from "./CommunicationTimelineView";

function renderTimeline(
  resource: Resource<typeof timeline> = {
    data: timeline,
    error: null,
    loading: false,
  },
) {
  const onRetry = vi.fn();
  render(
    <CommunicationTimelineView
      timeline={resource}
      contactOptions={[
        {
          canonicalIdentityId: 1,
          displayName: "Avery",
        },
      ]}
      selectedContactId={null}
      onContactChange={vi.fn()}
      onRetry={onRetry}
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
    expect(chart.querySelector('[fill="var(--color-brand-strong)"]')).toBeTruthy();
    expect(
      chart.querySelector('[fill="var(--color-timeline-contact)"]'),
    ).toBeTruthy();
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
