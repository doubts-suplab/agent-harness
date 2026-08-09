"""OpenAI-compatible HTTP `LlmPort` adapter + a provider preset registry (spec §7).

Most modern providers speak the OpenAI chat-completions wire format, so a single adapter parameterised
by ``base_url`` covers OpenAI, Groq, Ollama, Gemini (its OpenAI-compat endpoint) and Sarvam AI — adding
a compatible provider is *config, not code* (see :data:`PROVIDERS`). Anthropic is not OpenAI-compatible
natively; use :mod:`halo_agent_harness.adapters.llm_anthropic`.

The default transport is an async ``httpx`` client (install the ``llm`` extra:
``pip install "agent-harness[llm]"``); ``httpx`` is imported lazily, so merely importing this module
never requires it. Inject a ``transport`` to test offline (no network, no ``httpx``). API keys come from
the environment — never hardcoded. Streaming is deferred; use ``complete``.

The preset base URLs / default models are best-effort as of authoring and move fast — verify against the
provider's live docs before relying on them.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Awaitable, Callable

from ..ports.llm import CompletionResult, Message, ToolCall, ToolDefinition

# An async transport sends one HTTP request and returns (status_code, body_bytes). Injectable for tests.
Transport = Callable[[str, str, dict, bytes], Awaitable["tuple[int, bytes]"]]


class LlmError(RuntimeError):
    """A provider returned a non-2xx response or an unparseable body."""


async def httpx_transport(method: str, url: str, headers: dict, body: bytes, *, timeout: float = 30.0):
    """Default async transport (httpx). Returns (status, body) — non-2xx is surfaced by the caller."""
    import httpx  # lazily imported: only needed for real network calls (the 'llm' extra)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(method, url, headers=headers, content=body)
        return resp.status_code, resp.content


class OpenAICompatibleLlm:
    """`LlmPort` adapter for any OpenAI-compatible chat-completions endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str | None = None,
        api_key_env: str | None = None,
        provider_name: str = "openai-compatible",
        transport: Transport | None = None,
        timeout: float = 30.0,
        extra_headers: dict | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self.provider_name = provider_name
        self._api_key = api_key or (os.environ.get(api_key_env) if api_key_env else None)
        self._transport = transport or (lambda m, u, h, b: httpx_transport(m, u, h, b, timeout=timeout))
        self._extra_headers = dict(extra_headers or {})

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        payload: dict = {
            "model": self.model,
            "messages": _openai_messages(messages, system),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = [_openai_tool(t) for t in tools]

        status, body = await self._transport(
            "POST", f"{self._base_url}/chat/completions", self._headers(), _dump(payload)
        )
        if status >= 400:
            raise LlmError(f"{self.provider_name} returned HTTP {status}: {body.decode('utf-8', 'replace')[:500]}")
        return _parse_openai_response(json.loads(body), provider=self.provider_name, fallback_model=self.model)

    async def stream(self, messages, system=None, max_tokens=4096, temperature=0.7):
        raise NotImplementedError("streaming is deferred (roadmap Increment 4); use complete()")
        yield ""  # pragma: no cover — makes this an async generator

    # -- internals ------------------------------------------------------
    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json", **self._extra_headers}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers


@dataclass(frozen=True)
class ProviderPreset:
    """Base URL + auth + default model for an OpenAI-compatible provider."""

    provider_name: str
    base_url: str
    api_key_env: str | None
    default_model: str


# Best-effort presets — verify against live provider docs before relying on them.
PROVIDERS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset("openai", "https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o-mini"),
    "groq": ProviderPreset("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    "ollama": ProviderPreset("ollama", "http://localhost:11434/v1", None, "llama3.1"),
    "gemini": ProviderPreset(
        "gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-1.5-flash"
    ),
    "sarvam": ProviderPreset("sarvam", "https://api.sarvam.ai/v1", "SARVAM_API_KEY", "sarvam-m"),
}


def openai_compatible(
    provider: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    transport: Transport | None = None,
    timeout: float = 30.0,
) -> OpenAICompatibleLlm:
    """Build an :class:`OpenAICompatibleLlm` from a named preset in :data:`PROVIDERS`."""
    try:
        preset = PROVIDERS[provider]
    except KeyError:
        raise KeyError(f"unknown provider {provider!r}; known: {sorted(PROVIDERS)}") from None
    return OpenAICompatibleLlm(
        preset.base_url,
        model or preset.default_model,
        api_key=api_key,
        api_key_env=preset.api_key_env,
        provider_name=preset.provider_name,
        transport=transport,
        timeout=timeout,
    )


# -- request/response mapping (module-level, pure, easily testable) ----------
def _openai_messages(messages: list[Message], system: str | None) -> list[dict]:
    out: list[dict] = []
    if system:
        out.append({"role": "system", "content": system})
    out.extend({"role": m.role, "content": m.content} for m in messages)
    return out


def _openai_tool(tool: ToolDefinition) -> dict:
    return {
        "type": "function",
        "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
    }


def _parse_openai_response(data: dict, *, provider: str, fallback_model: str) -> CompletionResult:
    choices = data.get("choices") or [{}]
    message = choices[0].get("message", {}) if choices else {}
    tool_calls = []
    for call in message.get("tool_calls") or []:
        fn = call.get("function", {})
        raw_args = fn.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except (json.JSONDecodeError, TypeError):
            arguments = {}
        tool_calls.append(ToolCall(name=fn.get("name", ""), arguments=arguments, id=call.get("id", "")))
    usage = data.get("usage") or {}
    return CompletionResult(
        content=message.get("content") or "",
        tool_calls=tool_calls,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        model=data.get("model", fallback_model),
        provider=provider,
    )


def _dump(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")
