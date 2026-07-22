"""Shared test fixtures — a configurable fake agent and a harness wired to inspectable adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pytest

from agent_harness import (
    Agent,
    AgentInput,
    AuthorityLevel,
    ConfidenceGate,
    Decision,
    DecisionAction,
    Harness,
    ToolRegistry,
)
from agent_harness.adapters import (
    InMemoryAudit,
    InMemoryHumanReview,
    InMemoryKillSwitch,
    InMemoryObservability,
)
from agent_harness.core.agent import ToolInvoker


@dataclass
class FakeAgent:
    """A minimal Agent implementation whose decision is produced by an injected callable."""

    name: str
    authority_level: AuthorityLevel
    capabilities: frozenset[DecisionAction]
    decide: Callable[[AgentInput, ToolInvoker], Decision]

    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        return self.decide(request, tools)


def static_decision(action: DecisionAction, confidence: float, rationale: str = "because") -> Callable:
    def _decide(_request: AgentInput, _tools: ToolInvoker) -> Decision:
        return Decision(action=action, confidence=confidence, rationale=rationale)

    return _decide


@dataclass
class Rig:
    """Bundle of a harness plus the concrete adapters it was wired with, for assertions."""

    harness: Harness
    registry: ToolRegistry
    audit: InMemoryAudit
    review: InMemoryHumanReview
    obs: InMemoryObservability
    kill: InMemoryKillSwitch


@pytest.fixture
def rig() -> Rig:
    registry = ToolRegistry()
    audit = InMemoryAudit()
    review = InMemoryHumanReview()
    obs = InMemoryObservability()
    kill = InMemoryKillSwitch()
    harness = Harness(
        registry,
        audit=audit,
        human_review=review,
        observability=obs,
        kill_switch=kill,
        gate=ConfidenceGate(),
    )
    return Rig(harness=harness, registry=registry, audit=audit, review=review, obs=obs, kill=kill)


@pytest.fixture
def request_() -> AgentInput:
    return AgentInput(
        tenant_id="t1",
        user_id="u1",
        context={"task": "demo"},
        metadata={"correlationId": "corr-123"},
    )
