import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
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
