"""Side-effect gating tests (spec §5.3, T-5). write/external tool calls are gated before execution."""

from __future__ import annotations

import pytest

from agent_harness import (
    AuthorityLevel,
    Decision,
    DecisionAction,
    SideEffectPolicy,
)
from conftest import FakeAgent

_ALL = frozenset({DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.DEFER})


def _tool_agent(name, authority, tool, confidence, *, call_confidence=None):
    """An agent that calls ``tool`` (optionally with a per-call confidence) then ALLOWs."""

    def decide(_req, tools):
        result = tools.call(tool, {"x": 1}, confidence=call_confidence)
        return Decision(DecisionAction.ALLOW, confidence, f"called {tool} -> {result}")

    return FakeAgent(name, authority, _ALL, decide)


# -- policy unit behaviour ---------------------------------------------------
def test_policy_ungated_classes_always_pass():
    policy = SideEffectPolicy()
    for cls in ("none", "read", None):
        assert policy.permits(cls, None, AuthorityLevel.OBSERVE) is True


def test_policy_gated_requires_threshold():
    policy = SideEffectPolicy()
    assert policy.permits("write", 0.84, AuthorityLevel.ALERT) is False
    assert policy.permits("write", 0.85, AuthorityLevel.ALERT) is True
    assert policy.permits("external", 0.94, AuthorityLevel.BLOCK) is False
    assert policy.permits("external", 0.95, AuthorityLevel.BLOCK) is True


def test_policy_missing_confidence_is_treated_as_zero():
    assert SideEffectPolicy().permits("write", None, AuthorityLevel.ALERT) is False


def test_policy_observe_agent_never_performs_side_effects():
    policy = SideEffectPolicy()
    assert policy.permits("write", 1.0, AuthorityLevel.OBSERVE) is False
    assert policy.permits("external", 1.0, AuthorityLevel.OBSERVE) is False


# -- harness-enforced gating -------------------------------------------------
def test_read_tool_is_not_gated(rig, request_):
    rig.registry.register_tool("lookup", lambda a: "row", side_effect="read")
    rig.registry.grant("a", {"lookup"})
    agent = _tool_agent("a", AuthorityLevel.ALERT, "lookup", 0.9)  # no confidence needed
    out = rig.harness.invoke(agent, request_)
    assert out.decision.action is DecisionAction.ALLOW
    assert rig.audit.security_events == ()


def test_write_tool_below_threshold_is_refused_before_execution(rig, request_):
    executed = []
    rig.registry.register_tool("save", lambda a: executed.append(a) or "ok", side_effect="write")
    rig.registry.grant("a", {"save"})
    agent = _tool_agent("a", AuthorityLevel.ALERT, "save", 0.9, call_confidence=0.5)
    out = rig.harness.invoke(agent, request_)

    assert executed == []  # the side effect never happened
    assert out.decision.action is DecisionAction.DEFER  # safe failure default
    assert out.decision.auto_enforced is False
    kinds = [e.kind for e in rig.audit.security_events]
    assert "side_effect_denied" in kinds


def test_write_tool_at_threshold_executes(rig, request_):
    executed = []
    rig.registry.register_tool("save", lambda a: executed.append(a) or "ok", side_effect="write")
    rig.registry.grant("a", {"save"})
    agent = _tool_agent("a", AuthorityLevel.ALERT, "save", 0.9, call_confidence=0.85)
    out = rig.harness.invoke(agent, request_)

    assert len(executed) == 1  # the write ran
    assert out.decision.action is DecisionAction.ALLOW
    assert rig.audit.security_events == ()


def test_external_tool_requires_higher_confidence(rig, request_):
    executed = []
    rig.registry.register_tool("api", lambda a: executed.append(a) or "ok", side_effect="external")
    rig.registry.grant("a", {"api"})
    # 0.85 clears write but not external (0.95).
    agent = _tool_agent("a", AuthorityLevel.BLOCK, "api", 0.9, call_confidence=0.85)
    out = rig.harness.invoke(agent, request_)
    assert executed == []
    assert out.decision.action is DecisionAction.DEFER
    assert any(e.kind == "side_effect_denied" for e in rig.audit.security_events)


def test_observe_agent_cannot_call_write_tool(rig, request_):
    executed = []
    rig.registry.register_tool("save", lambda a: executed.append(a) or "ok", side_effect="write")
    rig.registry.grant("obs", {"save"})
    agent = _tool_agent("obs", AuthorityLevel.OBSERVE, "save", 0.5, call_confidence=1.0)
    out = rig.harness.invoke(agent, request_)
    assert executed == []  # even at confidence 1.0, a read-only agent may not write
    assert any(e.kind == "side_effect_denied" for e in rig.audit.security_events)


def test_custom_policy_thresholds_are_honoured(request_):
    from agent_harness import Harness, ToolRegistry
    from agent_harness.adapters import (
        InMemoryAudit,
        InMemoryHumanReview,
        InMemoryKillSwitch,
        InMemoryObservability,
    )

    registry = ToolRegistry()
    audit = InMemoryAudit()
    registry.register_tool("save", lambda a: "ok", side_effect="write")
    registry.grant("a", {"save"})
    harness = Harness(
        registry,
        audit=audit,
        human_review=InMemoryHumanReview(),
        observability=InMemoryObservability(),
        kill_switch=InMemoryKillSwitch(),
        side_effect_policy=SideEffectPolicy(write_threshold=0.6),
    )
    agent = _tool_agent("a", AuthorityLevel.ALERT, "save", 0.9, call_confidence=0.65)
    out = harness.invoke(agent, request_)
    assert out.decision.action is DecisionAction.ALLOW  # 0.65 clears the lowered 0.6 write bar
    assert audit.security_events == ()
