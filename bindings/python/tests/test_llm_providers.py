"""Production LlmPort provider tests (spec §7) — offline via an injected transport."""

from __future__ import annotations

import asyncio
import json

import pytest

from agent_harness.adapters import (
    PROVIDERS,
    AnthropicLlm,
    LlmError,
    OpenAICompatibleLlm,
    openai_compatible,
)
from agent_harness.ports.llm import Message, ToolDefinition


class FakeTransport:
    """Records the last request and returns a canned (status, body)."""

    def __init__(self, status: int, body: dict):
        self.status = status
        self.body = json.dumps(body).encode()
        self.calls: list[dict] = []

    def __call__(self, method, url, headers, body):
        self.calls.append(
            {"method": method, "url": url, "headers": headers, "payload": json.loads(body)}
        )
        return self.status, self.body

    @property
    def last(self) -> dict:
        return self.calls[-1]


_OPENAI_OK = {
    "model": "gpt-4o-mini",
    "choices": [{"message": {"content": "hello", "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": "{\"q\": 1}"}}
    ]}}],
    "usage": {"prompt_tokens": 11, "completion_tokens": 3},
}


# -- OpenAI-compatible adapter -----------------------------------------------
def test_openai_complete_builds_request_and_parses_response():
    transport = FakeTransport(200, _OPENAI_OK)
    llm = OpenAICompatibleLlm("https://api.example.com/v1", "gpt-4o-mini",
                              api_key="sk-test", transport=transport)
    result = asyncio.run(llm.complete(
        [Message("user", "hi")],
        system="be brief",
        tools=[ToolDefinition("lookup", "look things up", {"type": "object"}, "read")],
    ))
    # request shape
    assert transport.last["url"] == "https://api.example.com/v1/chat/completions"
    assert transport.last["headers"]["Authorization"] == "Bearer sk-test"
    payload = transport.last["payload"]
    assert payload["messages"][0] == {"role": "system", "content": "be brief"}
    assert payload["messages"][1] == {"role": "user", "content": "hi"}
    assert payload["tools"][0]["function"]["name"] == "lookup"
    # response mapping
    assert result.content == "hello"
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].arguments == {"q": 1}
    assert (result.input_tokens, result.output_tokens) == (11, 3)


def test_openai_error_status_raises():
    llm = OpenAICompatibleLlm("https://x/v1", "m", api_key="k",
                              transport=FakeTransport(429, {"error": "rate limited"}))
    with pytest.raises(LlmError):
        asyncio.run(llm.complete([Message("user", "hi")]))


def test_no_api_key_omits_authorization_header():
    transport = FakeTransport(200, _OPENAI_OK)
    llm = OpenAICompatibleLlm("http://localhost:11434/v1", "llama3.1", transport=transport)
    asyncio.run(llm.complete([Message("user", "hi")]))
    assert "Authorization" not in transport.last["headers"]


def test_preset_registry_builds_expected_adapters():
    assert set(PROVIDERS) >= {"openai", "groq", "ollama", "gemini", "sarvam"}
    groq = openai_compatible("groq", api_key="gsk-x", transport=FakeTransport(200, _OPENAI_OK))
    assert groq.provider_name == "groq"
    assert groq.model == PROVIDERS["groq"].default_model


def test_preset_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-env")
    transport = FakeTransport(200, _OPENAI_OK)
    llm = openai_compatible("groq", transport=transport)
    asyncio.run(llm.complete([Message("user", "hi")]))
    assert transport.last["headers"]["Authorization"] == "Bearer gsk-env"


def test_unknown_provider_rejected():
    with pytest.raises(KeyError):
        openai_compatible("not-a-provider")


def test_streaming_is_deferred():
    llm = OpenAICompatibleLlm("https://x/v1", "m", api_key="k", transport=FakeTransport(200, _OPENAI_OK))

    async def _drain():
        async for _ in llm.stream([Message("user", "hi")]):
            pass

    with pytest.raises(NotImplementedError):
        asyncio.run(_drain())


# -- native Anthropic adapter ------------------------------------------------
_ANTHROPIC_OK = {
    "model": "claude-3-5-sonnet-latest",
    "content": [
        {"type": "text", "text": "sure"},
        {"type": "tool_use", "id": "t1", "name": "search", "input": {"q": "x"}},
    ],
    "usage": {"input_tokens": 7, "output_tokens": 2},
}


def test_anthropic_complete_builds_native_request_and_parses_blocks():
    transport = FakeTransport(200, _ANTHROPIC_OK)
    llm = AnthropicLlm("claude-3-5-sonnet-latest", api_key="sk-ant", transport=transport)
    result = asyncio.run(llm.complete(
        [Message("system", "be careful"), Message("user", "hi")],
        system="top-level system",
        tools=[ToolDefinition("search", "search", {"type": "object"}, "read")],
    ))
    payload = transport.last["payload"]
    # system pulled out of messages and merged; tools use input_schema
    assert payload["system"] == "top-level system\n\nbe careful"
    assert all(m["role"] != "system" for m in payload["messages"])
    assert payload["tools"][0]["input_schema"] == {"type": "object"}
    assert "max_tokens" in payload  # required by Anthropic
    # headers
    assert transport.last["headers"]["x-api-key"] == "sk-ant"
    assert transport.last["headers"]["anthropic-version"]
    assert transport.last["url"].endswith("/messages")
    # response mapping
    assert result.content == "sure"
    assert result.tool_calls[0].name == "search"
    assert result.tool_calls[0].arguments == {"q": "x"}
    assert (result.input_tokens, result.output_tokens) == (7, 2)


def test_anthropic_api_key_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    transport = FakeTransport(200, _ANTHROPIC_OK)
    llm = AnthropicLlm(transport=transport)
    asyncio.run(llm.complete([Message("user", "hi")]))
    assert transport.last["headers"]["x-api-key"] == "sk-ant-env"
