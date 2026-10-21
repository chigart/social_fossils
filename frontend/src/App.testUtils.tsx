import { render, screen, within } from "@testing-library/react";
import App from "./App";

export async function renderLoadedDashboard() {
  render(<App />);
  await screen.findByRole("row", { name: /Aurora group/ });
}

export function rowTitles(table: HTMLElement) {
  const body = table.querySelector("tbody");
  if (!body) throw new Error("Expected the table to contain a body.");

  return within(body)
    .getAllByRole("row")
    .map((row) => within(row).getByRole("rowheader").textContent);
}
