import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AIChatPanel } from "../components/AIChatPanel";

const api = vi.hoisted(() => ({
  getOllamaModels: vi.fn(),
  sendAIChat: vi.fn(),
}));

vi.mock("../api", () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.getOllamaModels.mockResolvedValue({ models: ["qwen2.5:7b"] });
  api.sendAIChat.mockResolvedValue({ answer: "The aggregate trend increased." });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AIView", () => {
  it("discovers a local model without including dashboard state in chat requests", async () => {
    const user = userEvent.setup();
    render(<AIChatPanel active />);

    await screen.findByRole("option", { name: "qwen2.5:7b" });
    await user.type(
      screen.getByRole("textbox", { name: "Your question" }),
      "How has communication changed?",
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("The aggregate trend increased.")).toBeInTheDocument();
    expect(api.sendAIChat).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: "ollama",
        model: "qwen2.5:7b",
        messages: [
          { role: "user", content: "How has communication changed?" },
        ],
      }),
    );
    expect(api.sendAIChat.mock.calls[0][0]).not.toHaveProperty("context");
  });

  it("sends on Enter and keeps Shift+Enter available for new lines", async () => {
    const user = userEvent.setup();
    render(<AIChatPanel active />);
    await screen.findByRole("option", { name: "qwen2.5:7b" });

    const prompt = screen.getByRole("textbox", { name: "Your question" });
    await user.type(prompt, "First line");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    await user.type(prompt, "Second line");

    expect(prompt).toHaveValue("First line\nSecond line");
    await user.keyboard("{Enter}");

    expect(await screen.findByText("The aggregate trend increased.")).toBeInTheDocument();
    expect(api.sendAIChat).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [
          { role: "user", content: "First line\nSecond line" },
        ],
      }),
    );
  });

  it("scrolls the received answer to the top of the conversation", async () => {
    const user = userEvent.setup();
    const rectAt = (top: number): DOMRect =>
      ({
        x: 0,
        y: top,
        width: 100,
        height: 40,
        top,
        right: 100,
        bottom: top + 40,
        left: 0,
        toJSON: () => ({}),
      }) as DOMRect;
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
      function (this: HTMLElement) {
        if (this.getAttribute("role") === "log") return rectAt(100);
        if (
          this.tagName === "ARTICLE" &&
          this.textContent?.includes("The aggregate trend increased.")
        ) {
          return rectAt(320);
        }
        return rectAt(0);
      },
    );
    render(<AIChatPanel active />);
    await screen.findByRole("option", { name: "qwen2.5:7b" });
    await user.type(
      screen.getByRole("textbox", { name: "Your question" }),
      "What changed?",
    );
    await user.keyboard("{Enter}");

    await screen.findByText("The aggregate trend increased.");
    expect(screen.getByRole("log")).toHaveProperty("scrollTop", 220);
  });

  it("sends a cloud key only with a chat request", async () => {
    const user = userEvent.setup();
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    render(<AIChatPanel active />);
    await screen.findByRole("option", { name: "qwen2.5:7b" });

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Provider" }),
      "openai-compatible",
    );
    await user.clear(screen.getByRole("textbox", { name: "Model identifier" }));
    await user.type(
      screen.getByRole("textbox", { name: "Model identifier" }),
      "example-model",
    );
    await user.type(screen.getByLabelText("API key"), "temporary-key");
    await user.type(
      screen.getByRole("textbox", { name: "Your question" }),
      "Summarize my overview.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(api.sendAIChat).toHaveBeenCalledOnce());
    expect(api.sendAIChat).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: "openai-compatible",
        model: "example-model",
        api_key: "temporary-key",
        base_url: "https://api.openai.com/v1",
      }),
    );
    expect(setItem).not.toHaveBeenCalled();
    setItem.mockRestore();
  });
});
