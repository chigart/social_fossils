import { fireEvent, render, screen, within } from "@testing-library/react";
import App from "../App";

export async function renderLoadedDashboard() {
  render(<App />);
  await screen.findByText("All messages");
}

export async function selectDashboardTab(label: string) {
  fireEvent.click(screen.getByRole("tab", { name: label }));
  await screen.findByRole("tabpanel", { name: label });
}

export function rowTitles(table: HTMLElement) {
  const body = table.querySelector("tbody");
  if (!body) throw new Error("Expected the table to contain a body.");

  return within(body)
    .getAllByRole("row")
    .map((row) => within(row).getByRole("rowheader").textContent);
}
