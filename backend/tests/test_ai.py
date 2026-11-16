import asyncio
import json

import pytest
from fastapi import HTTPException
from mcp import Client
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from analytics_test_helpers import add_account, add_chat, add_message
from app.ai import mcp_tools, providers
from app.main import app
from app.schemas.ai import AIChatRequest, AIMessage


@pytest.fixture
def ai_session_factory(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'ai-test.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE account ("
                "id INTEGER PRIMARY KEY, name VARCHAR(200), "
                "platform VARCHAR(50) DEFAULT 'telegram', "
                "platform_user_id VARCHAR(100), username VARCHAR(100), "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE contacts ("
                "id INTEGER PRIMARY KEY, account_id INTEGER, "
                "platform VARCHAR(50) DEFAULT 'telegram', "
                "platform_user_id VARCHAR(100), source_contact_key VARCHAR(64), "
                "canonical_identity_id INTEGER, display_name VARCHAR(300), "
                "username VARCHAR(100), created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE canonical_identities ("
                "id INTEGER PRIMARY KEY, platform VARCHAR(50), "
                "platform_user_id VARCHAR(100), identity_group_id INTEGER)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE chats ("
                "id INTEGER PRIMARY KEY, account_id INTEGER, "
                "platform VARCHAR(50) DEFAULT 'telegram', "
                "chat_id VARCHAR(500), title VARCHAR(300), chat_type VARCHAR(50))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE messages ("
                "id INTEGER PRIMARY KEY, chat_id INTEGER, "
                "platform VARCHAR(50) DEFAULT 'telegram', "
                "source_record_key VARCHAR(64), source_reply_id VARCHAR(200), "
                "message_id VARCHAR(100), sender_id VARCHAR(100), "
                "sender_contact_id INTEGER, sender_name VARCHAR(300), "
                "is_outgoing BOOLEAN, message_date DATETIME, "
                "message_type VARCHAR(50), text_content TEXT, "
                "reply_to_telegram_message_id VARCHAR(100), raw_payload JSON)"
            )
        )
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def _call_tool(name: str, arguments: dict | None = None):
    async def call():
        async with Client(mcp_tools.mcp_server) as client:
            return await client.call_tool(name, arguments or {})

    return asyncio.run(call())


def test_mcp_tools_expose_only_aggregate_analytics(ai_session_factory, monkeypatch):
    with ai_session_factory() as db:
        add_account(db, 1, "synthetic-owner", name="Synthetic account", username="owner")
        add_chat(
            db,
            10,
            1,
            "synthetic-chat-id",
            "Synthetic private title",
            chat_type="personal_chat",
        )
        add_message(
            db,
            100,
            10,
            "message",
            "synthetic-peer",
            sender_contact_id=20,
            text_content="synthetic private message text",
        )
        db.execute(
            text(
                "INSERT INTO contacts "
                "(id, account_id, platform, platform_user_id, display_name, username) "
                "VALUES (20, 1, 'telegram', 'synthetic-contact-id', "
                "'Synthetic User', 'synthetic_handle')"
            )
        )
        db.commit()
    monkeypatch.setattr(
        mcp_tools,
        "SessionLocal",
        ai_session_factory,
    )

    async def list_tools():
        async with Client(mcp_tools.mcp_server) as client:
            return await client.list_tools()

    tools = asyncio.run(list_tools())
    assert {tool.name for tool in tools.tools} == {
        "list_accounts",
        "search_users",
        "get_overview_summary",
        "get_top_chat_metrics",
        "get_selected_chat_metrics",
        "get_chat_messages",
        "get_communication_balance_summary",
        "get_forgotten_contact_summary",
    }

    overview = _call_tool("get_overview_summary").structured_content
    accounts = _call_tool("list_accounts", {"limit": 10}).structured_content
    users = _call_tool("search_users", {"query": "SYNTHETIC_HANDLE"}).structured_content
    top_chats = _call_tool("get_top_chat_metrics", {"limit": 5}).structured_content
    selected_chat = _call_tool("get_selected_chat_metrics", {"chat_id": 10}).structured_content
    balance = _call_tool("get_communication_balance_summary").structured_content
    forgotten = _call_tool("get_forgotten_contact_summary").structured_content
    serialized = json.dumps(
        [accounts, users, overview, top_chats, selected_chat, balance, forgotten]
    )

    assert accounts["result"] == [
        {
            "account_id": 1,
            "platform": "telegram",
            "account_name": "Synthetic account",
            "username": "owner",
        }
    ]
    assert users["result"] == [
        {
            "contact_id": 20,
            "account_id": 1,
            "platform": "telegram",
            "display_name": "Synthetic User",
            "username": "synthetic_handle",
            "account_name": "Synthetic account",
            "account_username": "owner",
        }
    ]
    assert overview["total_messages"] == 1
    assert "synthetic private message text" not in serialized
    assert "Synthetic private title" not in json.dumps(
        [accounts, users, overview, top_chats, balance, forgotten]
    )
    assert "synthetic-owner" not in serialized
    assert "Synthetic User" in serialized
    assert "synthetic_handle" in serialized
    assert selected_chat["chat_id"] == 10
    assert selected_chat["chat_title"] == "Synthetic private title"
    assert selected_chat["account_name"] == "Synthetic account"
    assert selected_chat["total_messages"] == 1
    assert selected_chat["participants"] == [
        {
            "contact_id": 20,
            "display_name": "Synthetic User",
            "username": "synthetic_handle",
        }
    ]
    assert balance["eligible_contacts"] == 0
    assert forgotten["eligible_contacts"] == 0


def test_search_users_filters_platform_and_limits_results(
    ai_session_factory,
    monkeypatch,
):
    with ai_session_factory() as db:
        add_account(db, 1, "synthetic-owner")
        db.execute(
            text(
                "INSERT INTO contacts "
                "(id, account_id, platform, display_name, username) VALUES "
                "(20, 1, 'telegram', 'Ada Synthetic', 'ada_s'), "
                "(21, 1, 'telegram', 'Bea Synthetic', 'bea_s')"
            )
        )
        db.commit()
    monkeypatch.setattr(mcp_tools, "SessionLocal", ai_session_factory)

    results = _call_tool(
        "search_users",
        {"query": "synthetic", "platform": "telegram", "limit": 1},
    ).structured_content

    assert len(results["result"]) == 1
    assert results["result"][0]["contact_id"] == 20
    assert results["result"][0]["display_name"] == "Ada Synthetic"


def test_chat_uses_mcp_tool_results_without_raw_message_text(
    ai_session_factory,
    monkeypatch,
):
    with ai_session_factory() as db:
        add_account(db, 1, "synthetic-owner")
        add_chat(
            db,
            10,
            1,
            "synthetic-chat-id",
            "Synthetic private title",
            chat_type="personal_chat",
        )
        add_message(
            db,
            100,
            10,
            "message",
            "synthetic-peer",
            text_content="synthetic private message text",
        )
        db.commit()
    monkeypatch.setattr(
        mcp_tools,
        "SessionLocal",
        ai_session_factory,
    )

    observed_messages = []
    observed_tools = []

    def fake_provider_response(request, messages, tools):
        observed_messages.append(messages)
        observed_tools.append(tools)
        if len(observed_messages) == 1:
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-overview",
                        "function": {
                            "name": "get_overview_summary",
                            "arguments": "{}",
                        },
                    }
                ],
            }
        return {"content": "The dataset contains one message.", "tool_calls": []}

    monkeypatch.setattr(providers, "_provider_response", fake_provider_response)
    request = AIChatRequest(
        provider="openai-compatible",
        model="example-model",
        api_key="temporary-key",
        messages=[AIMessage(role="user", content="How much data is imported?")],
    )

    answer = providers.run_chat(request)

    assert answer == "The dataset contains one message."
    assert "get_overview_summary" in {
        tool["function"]["name"] for tool in observed_tools[0]
    }
    assert "get_chat_messages" not in {
        tool["function"]["name"] for tool in observed_tools[0]
    }
    second_request = json.dumps(observed_messages[1])
    assert "total_messages" in second_request
    assert "synthetic private message text" not in second_request
    assert "Synthetic private title" not in second_request
    assert "cannot access or quote raw message text" in observed_messages[0][0]["content"]


def test_local_ollama_can_use_raw_message_text_tool(
    ai_session_factory,
    monkeypatch,
):
    with ai_session_factory() as db:
        add_account(db, 1, "synthetic-owner")
        add_chat(
            db,
            10,
            1,
            "synthetic-chat-id",
            "Synthetic private title",
            chat_type="personal_chat",
        )
        add_message(
            db,
            100,
            10,
            "message",
            "synthetic-peer",
            text_content="synthetic private message text",
        )
        db.commit()
    monkeypatch.setattr(mcp_tools, "SessionLocal", ai_session_factory)

    observed_messages = []
    observed_tools = []

    def fake_provider_response(request, messages, tools):
        observed_messages.append(messages)
        observed_tools.append(tools)
        if len(observed_messages) == 1:
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-messages",
                        "function": {
                            "name": "get_chat_messages",
                            "arguments": '{"chat_id": 10, "limit": 50}',
                        },
                    }
                ],
            }
        return {
            "content": "The message says hello.",
            "tool_calls": [],
        }

    monkeypatch.setattr(providers, "_provider_response", fake_provider_response)
    request = AIChatRequest(
        provider="ollama",
        model="qwen2.5:7b",
        messages=[AIMessage(role="user", content="Analyze chat 10.")],
    )

    assert providers.run_chat(request) == "The message says hello."
    assert "get_chat_messages" in {
        tool["function"]["name"] for tool in observed_tools[0]
    }
    assert "synthetic private message text" in json.dumps(observed_messages[1])
    assert "local Ollama" in observed_messages[0][0]["content"]


def test_cloud_provider_cannot_call_local_message_tool(monkeypatch):
    monkeypatch.setattr(
        providers,
        "_provider_response",
        lambda request, messages, tools: {
            "content": None,
            "tool_calls": [
                {
                    "id": "call-private-messages",
                    "function": {
                        "name": "get_chat_messages",
                        "arguments": '{"chat_id": 10}',
                    },
                }
            ],
        },
    )
    request = AIChatRequest(
        provider="openai-compatible",
        model="example-model",
        api_key="temporary-key",
        messages=[AIMessage(role="user", content="Read chat 10.")],
    )

    with pytest.raises(HTTPException) as error:
        providers.run_chat(request)

    assert error.value.detail == (
        "The AI provider requested an unavailable analytics tool."
    )


def test_get_chat_messages_returns_bounded_ordinary_text_in_order(
    ai_session_factory,
    monkeypatch,
):
    with ai_session_factory() as db:
        add_account(db, 1, "synthetic-owner")
        add_chat(db, 10, 1, "synthetic-chat-id", "Chat", chat_type="personal_chat")
        add_message(db, 100, 10, "message", "peer", text_content="first text")
        add_message(db, 101, 10, "message", "peer", text_content="second text")
        add_message(db, 102, 10, "service", "peer", text_content="service text")
        db.commit()
    monkeypatch.setattr(mcp_tools, "SessionLocal", ai_session_factory)

    result = _call_tool(
        "get_chat_messages",
        {"chat_id": 10, "limit": 1},
    ).structured_content

    assert result["result"] == [
        {
            "timestamp": None,
            "is_outgoing": None,
            "sender": None,
            "text": "second text",
        }
    ]


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

    def fake_request(method, url, *, json, headers, timeout):
        observed.update(
            method=method,
            url=url,
            payload=json,
            headers=headers,
            timeout=timeout,
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
