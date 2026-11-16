import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.ai import providers
from app.main import app
from app.schemas.ai import AIChatRequest, AIMessage


def test_ollama_model_discovery_returns_names(monkeypatch):
    monkeypatch.setattr(
        providers.settings,
        "ollama_base_url",
        "http://host.docker.internal:11434/",
    )
    monkeypatch.setattr(
        providers,
        "_request_json",
        lambda method, url, **kwargs: {
            "models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2:3b"}]
        },
    )

    assert providers.get_ollama_models() == ["qwen2.5:7b", "llama3.2:3b"]


def test_ollama_connection_error_explains_docker_bind_address(monkeypatch):
    monkeypatch.setattr(
        providers.settings,
        "ollama_base_url",
        "http://host.docker.internal:11434",
    )

    def fail_request(*args, **kwargs):
        raise providers.requests.ConnectionError()

    monkeypatch.setattr(providers.requests, "request", fail_request)

    with pytest.raises(HTTPException) as error:
        providers.get_ollama_models()

    assert "Docker-reachable host address" in error.value.detail
    assert "not only 127.0.0.1" in error.value.detail


def test_openai_compatible_provider_sends_key_and_parses_reply(monkeypatch):
    observed = {}
    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443))
        ],
    )

    class Response:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {
                "choices": [
                    {"message": {"role": "assistant", "content": "Ready."}}
                ]
            }

    def fake_request(method, url, *, json, headers, timeout, allow_redirects):
        observed.update(
            method=method,
            url=url,
            payload=json,
            headers=headers,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
        return Response()

    monkeypatch.setattr(providers.requests, "request", fake_request)
    request = AIChatRequest(
        provider="openai-compatible",
        model="example-model",
        api_key="temporary-key",
        base_url="https://models.example/v1/",
        messages=[AIMessage(role="user", content="Analyze the overview.")],
    )

    message = providers._provider_response(request, [], [])

    assert message["content"] == "Ready."
    assert observed["method"] == "POST"
    assert observed["url"] == "https://models.example/v1/chat/completions"
    assert observed["headers"]["Authorization"] == "Bearer temporary-key"
    assert observed["payload"]["model"] == "example-model"
    assert observed["allow_redirects"] is False


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1"],
)
def test_cloud_base_url_rejects_non_public_ip_addresses(address):
    with pytest.raises(HTTPException) as error:
        providers._validate_public_base_url(f"https://{address}/v1")

    assert error.value.status_code == 422


def test_cloud_base_url_rejects_private_dns_resolution(monkeypatch):
    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (2, 1, 6, "", ("192.168.1.10", 443)),
        ],
    )

    with pytest.raises(HTTPException, match="only to public addresses"):
        providers._validate_public_base_url("https://models.example/v1")


def test_chat_timeout_is_bounded_by_remaining_request_deadline(monkeypatch):
    monkeypatch.setattr(providers.time, "monotonic", lambda: 25.0)

    assert providers._remaining_request_timeout(deadline=30.0) == 5.0

    monkeypatch.setattr(providers.time, "monotonic", lambda: 30.0)
    with pytest.raises(HTTPException) as error:
        providers._remaining_request_timeout(deadline=30.0)
    assert error.value.status_code == 504


def test_chat_rejects_malformed_tool_call_items(monkeypatch):
    monkeypatch.setattr(
        providers,
        "_provider_response",
        lambda request, messages, tools, *, timeout: {
            "content": None,
            "tool_calls": [None],
        },
    )
    request = AIChatRequest(
        provider="openai-compatible",
        model="example-model",
        api_key="temporary-key",
        messages=[AIMessage(role="user", content="Analyze my overview.")],
    )

    with pytest.raises(HTTPException) as error:
        providers.run_chat(request)

    assert error.value.status_code == 502
    assert error.value.detail == "The AI provider returned malformed tool calls."


def test_provider_errors_do_not_echo_api_key(monkeypatch):
    class Response:
        ok = False
        status_code = 401

    monkeypatch.setattr(
        providers.requests,
        "request",
        lambda *args, **kwargs: Response(),
    )

    with pytest.raises(HTTPException) as error:
        providers._request_json(
            "POST",
            "https://models.example/v1/chat/completions",
            payload={},
            api_key="temporary-key",
        )

    assert error.value.detail == "The AI provider returned HTTP 401."
    assert "temporary-key" not in error.value.detail


def test_openai_compatible_chat_requires_an_api_key():
    request = AIChatRequest(
        provider="openai-compatible",
        model="example-model",
        messages=[AIMessage(role="user", content="Analyze my overview.")],
    )

    with pytest.raises(HTTPException) as error:
        providers.run_chat(request)
    assert error.value.detail == (
        "An API key is required for the OpenAI-compatible provider."
    )


def test_chat_request_rejects_dashboard_context():
    with pytest.raises(ValidationError):
        AIChatRequest.model_validate(
            {
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "messages": [
                    {"role": "user", "content": "Analyze all my data."}
                ],
                "context": {
                    "active_view": "chats",
                    "platform_filter": "telegram",
                },
            }
        )


def test_ai_endpoints_are_registered():
    assert {"/api/ai/models", "/api/ai/chat"} <= set(app.openapi()["paths"])
