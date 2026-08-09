"""Native Anthropic Messages `LlmPort` adapter (spec §7).

Anthropic is not OpenAI-compatible on the wire: the system prompt is a top-level field, tool schemas use
``input_schema``, and responses are a list of ``content`` blocks (``text`` and ``tool_use``). This adapter
maps the harness ``LlmPort`` shape onto that API natively.

The default transport is the shared async ``httpx`` client (the ``llm`` extra); ``httpx`` is imported
lazily. Inject a ``transport`` to test offline. The API key comes from ``ANTHROPIC_API_KEY`` — never
hardcoded. Streaming is deferred; use ``complete``.
"""

from __future__ import annotations

import json
import os

from ..ports.llm import CompletionResult, Message, ToolCall, ToolDefinition
from .llm_http import LlmError, Transport, httpx_transport

_DEFAULT_VERSION = "2023-06-01"


class AnthropicLlm:
    """`LlmPort` adapter for the native Anthropic Messages API."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-latest",
        *,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com/v1",
        transport: Transport | None = None,
        timeout: float = 30.0,
        anthropic_version: str = _DEFAULT_VERSION,
    ) -> None:
        self.model = model
        self.provider_name = "anthropic"
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._transport = transport or (lambda m, u, h, b: httpx_transport(m, u, h, b, timeout=timeout))
        self._version = anthropic_version

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        # Anthropic keeps the system prompt out of the message list; pull any system-role messages out too.
        system_text = _merge_system(system, messages)
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages if m.role != "system"],
        }
        if system_text:
            payload["system"] = system_text
        if tools:
            payload["tools"] = [_anthropic_tool(t) for t in tools]

        status, body = await self._transport(
            "POST", f"{self._base_url}/messages", self._headers(), _dump(payload)
        )
        if status >= 400:
            raise LlmError(f"anthropic returned HTTP {status}: {body.decode('utf-8', 'replace')[:500]}")
        return _parse_anthropic_response(json.loads(body), fallback_model=self.model)

    async def stream(self, messages, system=None, max_tokens=4096, temperature=0.7):
        raise NotImplementedError("streaming is deferred (roadmap Increment 4); use complete()")
        yield ""  # pragma: no cover — makes this an async generator

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json", "anthropic-version": self._version}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers


# -- request/response mapping (pure) -----------------------------------------
def _merge_system(system: str | None, messages: list[Message]) -> str:
    parts = [system] if system else []
    parts.extend(m.content for m in messages if m.role == "system")
    return "\n\n".join(p for p in parts if p)


def _anthropic_tool(tool: ToolDefinition) -> dict:
    return {"name": tool.name, "description": tool.description, "input_schema": tool.parameters}


def _parse_anthropic_response(data: dict, *, fallback_model: str) -> CompletionResult:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in data.get("content") or []:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append(
                ToolCall(name=block.get("name", ""), arguments=block.get("input") or {}, id=block.get("id", ""))
            )
    usage = data.get("usage") or {}
    return CompletionResult(
        content="".join(text_parts),
        tool_calls=tool_calls,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        model=data.get("model", fallback_model),
        provider="anthropic",
    )


def _dump(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")
