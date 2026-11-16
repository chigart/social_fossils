import type { useAIChat } from "../hooks/useAIChat";

type AIViewProps = ReturnType<typeof useAIChat>;

export function AIView({
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
  handleProviderChange,
  handleOllamaModelChange,
  handleOpenAIModelChange,
  handleApiBaseUrlChange,
  handleApiKeyChange,
  handlePromptChange,
  handleSubmit,
  handleClear,
}: AIViewProps) {

  return (
    <section
      className="mx-auto max-w-[900px] rounded-2xl border border-border bg-surface p-6 shadow-sm max-sm:p-4"
      aria-labelledby="ai-title"
    >
      <header className="mb-5">
        <p className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
          ANALYSIS ASSISTANT
        </p>
        <h2
          id="ai-title"
          className="mt-1 text-section-heading font-semibold text-ink"
        >
          Ask about your communication patterns
        </h2>
        <p className="mt-2 text-small text-ink-muted">
          The assistant chooses from read-only aggregate analytics tools to
          answer your questions. It cannot access raw message text, and does
          not use the selected dashboard view or filters.
        </p>
      </header>

      <div className="mb-5 grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1.5 text-small font-medium text-ink">
          Provider
          <select
            className="rounded-lg border border-border bg-canvas px-3 py-2"
            value={provider}
            onChange={handleProviderChange}
          >
            <option value="ollama">Local Ollama</option>
            <option value="openai-compatible">OpenAI-compatible API</option>
          </select>
        </label>

        {provider === "ollama" ? (
          <label className="grid gap-1.5 text-small font-medium text-ink">
            Local model
            <select
              className="rounded-lg border border-border bg-canvas px-3 py-2"
              value={ollamaModel}
              onChange={handleOllamaModelChange}
              disabled={modelLoading || ollamaModels.length === 0}
            >
              {ollamaModels.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <span className="font-normal text-ink-muted">
              {modelLoading
                ? "Finding models on Ollama…"
                : ollamaModels.length === 0
                  ? "No local models found. Check Ollama and its Docker-accessible URL."
                  : "Models are discovered from your local Ollama instance."}
            </span>
            {modelError && (
              <span
                role="alert"
                className="font-normal text-ink-warning"
              >
                {modelError}
              </span>
            )}
          </label>
        ) : (
          <label className="grid gap-1.5 text-small font-medium text-ink">
            Model identifier
            <input
              className="rounded-lg border border-border bg-canvas px-3 py-2"
              value={openAIModel}
              onChange={handleOpenAIModelChange}
              autoComplete="off"
              required
            />
          </label>
        )}

        {provider === "openai-compatible" && (
          <>
            <label className="grid gap-1.5 text-small font-medium text-ink">
              API base URL
              <input
                className="rounded-lg border border-border bg-canvas px-3 py-2"
                value={apiBaseUrl}
                onChange={handleApiBaseUrlChange}
                placeholder="https://api.openai.com/v1"
                autoComplete="url"
              />
            </label>
            <div className="grid gap-1.5 text-small font-medium text-ink">
              <label htmlFor="ai-api-key">API key</label>
              <input
                id="ai-api-key"
                className="rounded-lg border border-border bg-canvas px-3 py-2"
                type="password"
                value={apiKey}
                onChange={handleApiKeyChange}
                autoComplete="off"
                required
              />
              <p className="font-normal text-ink-muted">
                Used only for chat requests and kept in this page session.
              </p>
            </div>
          </>
        )}
      </div>

      {provider === "openai-compatible" && (
        <p className="mb-4 rounded-lg bg-surface-muted px-3 py-2 text-caption text-ink-muted">
          Your question and aggregate analytics may be sent to the configured
          API provider. Raw message text is never included.
        </p>
      )}

      <div
        className="mb-4 max-h-[440px] min-h-[150px] space-y-3 overflow-y-auto rounded-xl border border-border bg-canvas p-4"
        role="log"
        aria-label="AI conversation"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <p className="text-small text-ink-muted">
            Ask a question about your imported communication analytics.
          </p>
        ) : (
          messages.map((message, index) => (
            <article
              className={`max-w-[90%] whitespace-pre-wrap rounded-xl px-3 py-2 text-small ${
                message.role === "user"
                  ? "ml-auto bg-surface-brand text-ink"
                  : "bg-surface text-ink"
              }`}
              key={`${message.role}-${index}`}
            >
              <p className="mb-1 text-caption font-semibold uppercase text-ink-muted">
                {message.role === "user" ? "You" : "AI"}
              </p>
              <p>{message.content}</p>
            </article>
          ))
        )}
        {chatLoading && (
          <p className="text-small text-ink-muted" role="status">
            Analyzing…
          </p>
        )}
      </div>

      {chatError && (
        <p
          className="mb-3 rounded-md bg-surface-warning p-3 text-small text-ink-warning"
          role="alert"
        >
          {chatError}
        </p>
      )}

      <form className="grid gap-3" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="ai-prompt">
          Your question
        </label>
        <textarea
          id="ai-prompt"
          className="min-h-24 resize-y rounded-xl border border-border bg-canvas p-3 text-small text-ink"
          value={prompt}
          onChange={handlePromptChange}
          maxLength={4000}
          placeholder="For example: How has my communication volume changed?"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            className="rounded-lg border border-border px-3 py-2 text-small text-ink-muted hover:bg-canvas"
            type="button"
            onClick={handleClear}
            disabled={messages.length === 0 || chatLoading}
          >
            Clear chat
          </button>
          <button
            className="rounded-lg bg-brand px-4 py-2 text-small font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            type="submit"
            disabled={!canSend || !prompt.trim()}
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
