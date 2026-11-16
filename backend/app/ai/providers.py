import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import requests
from fastapi import HTTPException
from mcp import Client
from mcp.server.mcpserver.exceptions import UnexpectedToolError

from app.ai.mcp_tools import mcp_server
from app.config import settings
from app.schemas.ai import AIChatRequest

MAX_TOOL_CALLS = 8
MAX_TOOL_ROUNDS = 6
REQUEST_TIMEOUT_SECONDS = 120

LOCAL_SYSTEM_PROMPT = (
    "You analyze Social Fossils communication analytics. Use the read-only "
    "analytics tools when database facts are needed. You may receive imported "
    "account names, contact display names and usernames, and aggregate "
    "statistics. Use search_chats to find a chat by its name, then use the "
    "returned chat_id with get_chat_messages to read its messages. Each message "
    "includes a user_id when available. Use get_chat_users to list the users "
    "who participated in a chat and match user IDs to names. You may retrieve "
    "and analyze raw message text and user IDs because this request is being "
    "handled by local Ollama. Ground conclusions in tool results, say when data "
    "is insufficient, and distinguish observed patterns from causation. If an "
    "analytics tool fails, say so and do not infer its result. Choose analytics "
    "tools based on the user's question. Do not assume or apply any current "
    "dashboard view, selection, or filter."
)

CLOUD_SYSTEM_PROMPT = (
    "You analyze Social Fossils communication analytics. Use the read-only "
    "analytics tools when database facts are needed. You may receive imported "
    "account names, contact display names and usernames, and aggregate "
    "statistics. You cannot access or quote raw message text. Do not claim to "
    "have read messages. Ground conclusions in tool results, say when data is "
    "insufficient, and distinguish observed patterns from causation. If an "
    "analytics tool fails, say so and do not infer its result. Choose analytics "
    "tools based on the user's question. Do not assume or apply any current "
    "dashboard view, selection, or filter."
)
LOCAL_ONLY_TOOL_NAMES = {
    "get_chat_messages",
    "get_chat_users",
    "search_chats",
}


def _validate_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status_code=422,
            detail="The model API base URL must be an HTTP(S) URL without credentials, query, or fragment.",
        )
    return value.rstrip("/")


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    api_key: str | None = None,
    connection_error: str = "Unable to connect to the selected AI provider.",
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = requests.request(
            method,
            url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=connection_error,
        ) from error

    if not response.ok:
        raise HTTPException(
            status_code=502,
            detail=f"The AI provider returned HTTP {response.status_code}.",
        )
    try:
        result = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="The AI provider returned invalid JSON.",
        ) from error
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=502,
            detail="The AI provider returned an invalid response.",
        )
    return result


def get_ollama_models() -> list[str]:
    base_url = _validate_base_url(settings.ollama_base_url)
    response = _request_json(
        "GET",
        f"{base_url}/api/tags",
        connection_error=(
            "Cannot connect to Ollama from the backend. Confirm Ollama is "
            "running and listening on a Docker-reachable host address, not "
            "only 127.0.0.1."
        ),
    )
    models = response.get("models")
    if not isinstance(models, list):
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an invalid model list.",
        )
    return [
        model["name"]
        for model in models
        if isinstance(model, dict)
        and isinstance(model.get("name"), str)
        and model["name"]
    ]


def _tool_definitions(tools: list[Any]) -> list[dict[str, Any]]:
    definitions = []
    for tool in tools:
        definition = tool.model_dump(mode="json", by_alias=True)
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": definition["name"],
                    "description": definition.get("description") or "",
                    "parameters": definition.get(
                        "inputSchema",
                        {"type": "object", "properties": {}},
                    ),
                },
            }
        )
    return definitions


def _provider_response(
    request: AIChatRequest,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "messages": messages,
        "tools": tools,
    }
    if request.provider == "ollama":
        payload["stream"] = False
        response = _request_json(
            "POST",
            f"{_validate_base_url(settings.ollama_base_url)}/api/chat",
            payload=payload,
            connection_error=(
                "Cannot connect to Ollama from the backend. Confirm Ollama is "
                "running and listening on a Docker-reachable host address, not "
                "only 127.0.0.1."
            ),
        )
        message = response.get("message")
    else:
        base_url = _validate_base_url(
            request.base_url or "https://api.openai.com/v1"
        )
        response = _request_json(
            "POST",
            f"{base_url}/chat/completions",
            payload=payload,
            api_key=request.api_key,
        )
        choices = response.get("choices")
        message = (
            choices[0].get("message")
            if isinstance(choices, list)
            and choices
            and isinstance(choices[0], dict)
            else None
        )

    if not isinstance(message, dict):
        raise HTTPException(
            status_code=502,
            detail="The AI provider returned an invalid chat response.",
        )
    return message


def _tool_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=502,
                detail="The AI provider returned malformed tool arguments.",
            ) from error
    if not isinstance(value, dict):
        raise HTTPException(
            status_code=502,
            detail="The AI provider returned malformed tool arguments.",
        )
    return value


def _tool_result_text(result: Any) -> str:
    if result.structured_content is not None:
        return json.dumps(result.structured_content, ensure_ascii=False)
    return json.dumps(
        [block.model_dump(mode="json", by_alias=True) for block in result.content],
        ensure_ascii=False,
    )


def _append_tool_result(
    provider: str,
    messages: list[dict[str, Any]],
    *,
    tool_name: str,
    tool_call_id: str,
    result_text: str,
) -> None:
    message: dict[str, Any] = {"role": "tool", "content": result_text}
    if provider == "ollama":
        message["tool_name"] = tool_name
    else:
        message["tool_call_id"] = tool_call_id
    messages.append(message)


async def _run_chat(request: AIChatRequest) -> str:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                LOCAL_SYSTEM_PROMPT
                if request.provider == "ollama"
                else CLOUD_SYSTEM_PROMPT
            ),
        },
        *[message.model_dump() for message in request.messages],
    ]

    async with Client(mcp_server) as client:
        tool_list = await client.list_tools()
        tool_definitions = _tool_definitions(tool_list.tools)
        if request.provider == "openai-compatible":
            tool_definitions = [
                tool
                for tool in tool_definitions
                if tool["function"]["name"] not in LOCAL_ONLY_TOOL_NAMES
            ]
        allowed_tool_names = {tool["function"]["name"] for tool in tool_definitions}
        tool_calls_used = 0
        tool_errors: list[str] = []
        unavailable_tool_requested = False

        for _ in range(MAX_TOOL_ROUNDS):
            assistant_message = _provider_response(
                request,
                messages,
                tool_definitions,
            )
            tool_calls = assistant_message.get("tool_calls") or []
            if not isinstance(tool_calls, list):
                raise HTTPException(
                    status_code=502,
                    detail="The AI provider returned malformed tool calls.",
                )
            if not tool_calls:
                answer = assistant_message.get("content")
                if not isinstance(answer, str) or not answer.strip():
                    raise HTTPException(
                        status_code=502,
                        detail="The AI provider returned an empty answer.",
                    )
                if tool_errors:
                    failed_tools = ", ".join(sorted(set(tool_errors)))
                    return (
                        f"I could not retrieve {failed_tools} because an "
                        f"analytics query failed. {answer}"
                    )
                return answer
            if tool_calls_used + len(tool_calls) > MAX_TOOL_CALLS:
                raise HTTPException(
                    status_code=502,
                    detail="The AI provider requested too many analytics tool calls.",
                )

            assistant_entry: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_message.get("content") or "",
                "tool_calls": tool_calls,
            }
            messages.append(assistant_entry)
            for index, tool_call in enumerate(tool_calls):
                function = tool_call.get("function")
                if not isinstance(function, dict):
                    raise HTTPException(
                        status_code=502,
                        detail="The AI provider returned a malformed tool call.",
                    )
                tool_name = function.get("name")
                if (
                    not isinstance(tool_name, str)
                    or tool_name not in allowed_tool_names
                ):
                    unavailable_tool_requested = True
                    break
                arguments = _tool_arguments(function.get("arguments", {}))
                try:
                    result = await client.call_tool(tool_name, arguments)
                except UnexpectedToolError:
                    tool_errors.append(tool_name)
                    tool_text = json.dumps(
                        {
                            "error": (
                                "The analytics query failed; no result was "
                                "available. Do not infer its result."
                            )
                        }
                    )
                else:
                    if result.is_error:
                        tool_errors.append(tool_name)
                    tool_text = _tool_result_text(result)
                call_id = tool_call.get("id")
                if not isinstance(call_id, str):
                    call_id = f"call_{tool_calls_used + index}"
                _append_tool_result(
                    request.provider,
                    messages,
                    tool_name=tool_name,
                    tool_call_id=call_id,
                    result_text=tool_text,
                )
                tool_calls_used += 1
            if unavailable_tool_requested:
                break

    if unavailable_tool_requested:
        raise HTTPException(
            status_code=502,
            detail="The AI provider requested an unavailable analytics tool.",
        )
    raise HTTPException(
        status_code=502,
        detail="The AI provider did not finish its answer after using analytics tools.",
    )


def run_chat(request: AIChatRequest) -> str:
    if request.provider == "openai-compatible":
        if not request.api_key or not request.api_key.strip():
            raise HTTPException(
                status_code=422,
                detail="An API key is required for the OpenAI-compatible provider.",
            )
        if len(request.api_key) > 5000:
            raise HTTPException(
                status_code=422,
                detail="The API key is too long.",
            )
    return asyncio.run(_run_chat(request))
