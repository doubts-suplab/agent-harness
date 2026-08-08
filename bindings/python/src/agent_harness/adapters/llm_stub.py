"""A deterministic stub LlmPort adapter for tests and local runs (spec §7).

Real deployments supply an Anthropic/Groq/Ollama adapter satisfying the same LlmPort Protocol.
"""

from __future__ import annotations

from typing import AsyncIterator

from ..ports.llm import CompletionResult, Message, ToolDefinition


class StubLlm:
    """Returns a canned completion; useful for exercising agents without a real provider."""

    def __init__(self, reply: str = "ok", provider_name: str = "stub", model: str = "stub-1") -> None:
        self._reply = reply
        self.provider_name = provider_name
        self.model = model

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        return CompletionResult(
            content=self._reply,
            input_tokens=sum(len(m.content.split()) for m in messages),
            output_tokens=len(self._reply.split()),
            model=self.model,
            provider=self.provider_name,
        )

    async def stream(
        self,
        messages: list[Message],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        for token in self._reply.split():
            yield token
