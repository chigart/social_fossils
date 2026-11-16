import { useEffect, useRef, useState } from "react";
import type {
  ChangeEventHandler,
  KeyboardEvent,
  KeyboardEventHandler,
  SubmitEvent,
  SubmitEventHandler,
} from "react";
import {
  getOllamaModels,
  sendAIChat,
  type AIMessage,
  type AIProvider,
} from "../api";

export function useAIChat(active: boolean) {
  const [provider, setProvider] = useState<AIProvider>("ollama");
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaModel, setOllamaModel] = useState("");
  const [openAIModel, setOpenAIModel] = useState("gpt-4o-mini");
  const [apiBaseUrl, setApiBaseUrl] = useState("https://api.openai.com/v1");
  const [apiKey, setApiKey] = useState("");
  const [modelLoading, setModelLoading] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const conversationRef = useRef<HTMLDivElement>(null);
  const latestAssistantMessageRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!active || provider !== "ollama") return;
    let cancelled = false;
    setModelLoading(true);
    setModelError(null);
    void getOllamaModels()
      .then(({ models }) => {
        if (cancelled) return;
        setOllamaModels(models);
        setOllamaModel((current) =>
          models.includes(current) ? current : (models[0] ?? ""),
        );
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setModelError(
          error instanceof Error ? error.message : "Unable to load Ollama models.",
        );
      })
      .finally(() => {
        if (!cancelled) setModelLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [active, provider]);

  const model = provider === "ollama" ? ollamaModel : openAIModel.trim();
  const canSend =
    !chatLoading &&
    Boolean(model) &&
    (provider === "ollama" || Boolean(apiKey.trim()));

  useEffect(() => {
    const conversation = conversationRef.current;
    const message = latestAssistantMessageRef.current;
    if (!conversation || !message) return;

    const conversationTop = conversation.getBoundingClientRect().top;
    const messageTop = message.getBoundingClientRect().top;
    conversation.scrollTop += messageTop - conversationTop;
  }, [messages]);

  const handleProviderChange: ChangeEventHandler<HTMLSelectElement> = (
    event,
  ) => {
    const value = event.currentTarget.value;
    if (value === "ollama" || value === "openai-compatible") {
      setProvider(value);
    }
  };
  const handleOllamaModelChange: ChangeEventHandler<HTMLSelectElement> = (
    event,
  ) => setOllamaModel(event.currentTarget.value);
  const handleOpenAIModelChange: ChangeEventHandler<HTMLInputElement> = (
    event,
  ) => setOpenAIModel(event.currentTarget.value);
  const handleApiBaseUrlChange: ChangeEventHandler<HTMLInputElement> = (
    event,
  ) => setApiBaseUrl(event.currentTarget.value);
  const handleApiKeyChange: ChangeEventHandler<HTMLInputElement> = (event) =>
    setApiKey(event.currentTarget.value);
  const handlePromptChange: ChangeEventHandler<HTMLTextAreaElement> = (event) =>
    setPrompt(event.currentTarget.value);

  const submitPrompt = async () => {
    const userPrompt = prompt.trim();
    if (!userPrompt || !canSend) return;

    const nextMessages: AIMessage[] = [
      ...messages,
      { role: "user", content: userPrompt },
    ];
    setMessages(nextMessages);
    setPrompt("");
    setChatError(null);
    setChatLoading(true);
    try {
      const response = await sendAIChat({
        provider,
        model,
        messages: nextMessages.slice(-20),
        ...(provider === "openai-compatible"
          ? { api_key: apiKey, base_url: apiBaseUrl.trim() || undefined }
          : {}),
      });
      setMessages([
        ...nextMessages,
        { role: "assistant", content: response.answer },
      ]);
    } catch (error) {
      setChatError(
        error instanceof Error ? error.message : "The AI request failed.",
      );
    } finally {
      setChatLoading(false);
    }
  };

  const handleSubmit: SubmitEventHandler<HTMLFormElement> = async (
    event: SubmitEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    await submitPrompt();
  };

  const handlePromptKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (
    event: KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();
    void submitPrompt();
  };

  const handleClear = () => {
    setMessages([]);
    setChatError(null);
  };

  return {
    provider,
    ollamaModels,
    ollamaModel,
    openAIModel,
    apiBaseUrl,
    apiKey,
    modelLoading,
    modelError,
    messages,
    prompt,
    chatLoading,
    chatError,
    canSend,
    conversationRef,
    latestAssistantMessageRef,
    handleProviderChange,
    handleOllamaModelChange,
    handleOpenAIModelChange,
    handleApiBaseUrlChange,
    handleApiKeyChange,
    handlePromptChange,
    handlePromptKeyDown,
    handleSubmit,
    handleClear,
  };
}
