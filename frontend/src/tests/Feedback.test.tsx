import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PaginationControls } from "../components/Feedback";
import { DEFAULT_PAGE_SIZE } from "../constants";

describe("PaginationControls", () => {
  it("shows page numbers, ellipses, and the final pages", () => {
    render(
      <PaginationControls
        pagination={{ page: 1, page_size: DEFAULT_PAGE_SIZE, total: 3400 }}
        onPageChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Go to page 1" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    for (const page of [2, 3, 4, 5, 66, 67, 68]) {
      expect(
        screen.getByRole("button", { name: `Go to page ${page}` }),
      ).toBeInTheDocument();
    }
    expect(screen.getAllByText("…")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Go to page 6" })).toBeNull();
  });

  it("navigates directly to a selected page", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <PaginationControls
        pagination={{ page: 1, page_size: DEFAULT_PAGE_SIZE, total: 3400 }}
        onPageChange={onPageChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Go to page 4" }));

    expect(onPageChange).toHaveBeenCalledWith(4);
  });
});
