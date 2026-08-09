"""LlmPort shape check (spec §7) — the stub adapter satisfies the port and round-trips."""

from __future__ import annotations

import asyncio

from halo_agent_harness.adapters import StubLlm
from halo_agent_harness.ports import LlmPort, Message


def test_stub_satisfies_llm_port():
    stub = StubLlm(reply="hello world")
    assert isinstance(stub, LlmPort)


def test_stub_complete_and_stream():
    stub = StubLlm(reply="hello world")

    result = asyncio.run(stub.complete([Message(role="user", content="hi there")]))
    assert result.content == "hello world"
    assert result.output_tokens == 2
    assert result.provider == "stub"

    async def collect() -> list[str]:
        return [tok async for tok in stub.stream([Message(role="user", content="hi")])]

    assert asyncio.run(collect()) == ["hello", "world"]
