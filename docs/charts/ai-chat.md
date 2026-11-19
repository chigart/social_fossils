# AI chat and data boundaries

```mermaid
flowchart TD
    Request["POST /api/ai/chat"]
    Provider{"Provider"}
    LocalPrompt["Use local-analysis system prompt"]
    CloudPrompt["Use cloud-safe system prompt"]
    Tools["List read-only MCP analytics tools"]
    Filter{"OpenAI-compatible provider?"}
    Remove["Remove search_chats,<br/>get_chat_users,<br/>get_chat_messages"]
    Keep["Keep aggregate and name-based<br/>analytics tools"]
    Call["Send prompt, conversation,<br/>and provider-allowed tools"]
    ToolCall{"Provider requests a tool?"}
    Validate["Check tool is allowed;<br/>validate arguments"]
    Execute["Execute read-only MCP query<br/>against PostgreSQL"]
    Error{"Tool query failed?"}
    ErrorText["Return explicit tool error;<br/>do not infer missing result"]
    Results["Append tool result and<br/>continue provider turn"]
    Answer["Return final answer"]
    Limit["Stop on tool-call, round,<br/>or request-time limit"]

    Request --> Provider
    Provider -->|"Ollama"| LocalPrompt
    Provider -->|"OpenAI-compatible"| CloudPrompt
    LocalPrompt --> Tools
    CloudPrompt --> Tools
    Tools --> Filter
    Filter -->|"Yes"| Remove --> Call
    Filter -->|"No"| Keep --> Call
    Call --> ToolCall
    ToolCall -->|"No, final response"| Answer
    ToolCall -->|"Yes"| Validate
    Validate --> Execute --> Error
    Error -->|"Yes"| ErrorText --> Results
    Error -->|"No"| Results
    Results --> Call
    Call -. "limits exceeded or malformed response" .-> Limit
```

Both providers can use read-only analytics tools for aggregates and account or
contact names. Only local Ollama receives the `search_chats`,
`get_chat_users`, and `get_chat_messages` tool definitions; these can expose
chat lookup, participant IDs, and raw message text. OpenAI-compatible requests
use a public HTTPS base URL and require an API key, which is supplied with the
request and is not persisted.

The server validates requested tool names and arguments, limits tool use to
eight calls and six rounds, and bounds the request duration. Analytics failures
are surfaced to the model as errors rather than fabricated values. Tools
cannot execute arbitrary SQL or mutate the database.
