"""Conformance suite — maps 1:1 to harness-protocol.md §9. Each test cites its checklist item."""

from __future__ import annotations

from datetime import timezone

import pytest

from agent_harness import (
    AgentInput,
    AuthorityLevel,
    BYPASS_COUNTER,
    ConfidenceGate,
    Decision,
    DecisionAction,
    SupervisorWorkers,
    ToolNotAuthorizedError,
    ToolRegistrationError,
    reconcile,
)
from conftest import FakeAgent, static_decision


# §9 — Envelope: one input in, one output out; tenant/user validated (§2) --------------------
def test_envelope_roundtrip(rig, request_):
    agent = FakeAgent("a", AuthorityLevel.ALERT, frozenset({DecisionAction.ALERT}),
                      static_decision(DecisionAction.ALERT, 0.9))
    out = rig.harness.invoke(agent, request_)
    assert out.agent_name == "a"
    assert out.executed_at.tzinfo == timezone.utc
    assert out.decision.action is DecisionAction.ALERT


@pytest.mark.parametrize("tenant,user", [("", "u"), ("t", ""), ("", "")])
def test_unscoped_invocation_is_rejected_not_defaulted(rig, tenant, user):
    from agent_harness import UnscopedInvocationError
    agent = FakeAgent("a", AuthorityLevel.OBSERVE, frozenset({DecisionAction.ALLOW}),
                      static_decision(DecisionAction.ALLOW, 0.9))
    with pytest.raises(UnscopedInvocationError):
        rig.harness.invoke(agent, AgentInput(tenant_id=tenant, user_id=user))


# §9 — Gate centralized: the agent cannot self-approve (§4, INV-1) ---------------------------
def test_agent_cannot_set_auto_enforced(rig, request_):
    def decide(_req, _tools):
        # Agent tries to self-approve a low-confidence BLOCK.
        return Decision(DecisionAction.BLOCK, 0.5, "block", auto_enforced=True)

    agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}), decide)
    out = rig.harness.invoke(agent, request_)
    assert out.decision.auto_enforced is False  # harness overrode the agent's flag


def test_high_confidence_within_authority_auto_enforces(rig, request_):
    agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}),
                      static_decision(DecisionAction.BLOCK, 0.96))
    out = rig.harness.invoke(agent, request_)
    assert out.decision.auto_enforced is True


# §9 — Gate non-disableable: no off switch; threshold floor is 0.80 (G-3, G-4) ---------------
def test_gate_has_no_disable_api():
    gate = ConfidenceGate()
    assert not any(hasattr(gate, n) for n in ("disable", "enabled", "off", "bypass"))


@pytest.mark.parametrize("authority", list(AuthorityLevel))
def test_threshold_never_below_base(authority):
    assert ConfidenceGate().threshold_for(authority) >= 0.80


# §9 — Low-confidence routing = 100% (§4 G-2) ------------------------------------------------
@pytest.mark.parametrize("confidence", [0.0, 0.3, 0.5, 0.79])
def test_low_confidence_always_routes_to_human(rig, request_, confidence):
    agent = FakeAgent("a", AuthorityLevel.ALERT, frozenset({DecisionAction.ALERT}),
                      static_decision(DecisionAction.ALERT, confidence))
    out = rig.harness.invoke(agent, request_)
    assert out.decision.auto_enforced is False
    assert len(rig.review.items) == 1
    assert rig.review.items[0].reason == "low_confidence"


# §9 — Gate bypass counter stays 0 (§4.2) ----------------------------------------------------
def test_bypass_counter_is_zero(rig, request_):
    for c in (0.0, 0.5, 0.8, 0.96, 1.0):
        agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}),
                          static_decision(DecisionAction.BLOCK, c))
        rig.harness.invoke(agent, request_)
    assert rig.obs.counter(BYPASS_COUNTER) == 0


# §9 — Tools default-deny; out-of-allowlist refused + security event (§5, INV-2) -------------
def test_unauthorized_tool_is_refused_and_logged(rig, request_):
    def decide(_req, tools):
        tools.call("db", {})  # not granted → raises inside run
        return Decision(DecisionAction.ALLOW, 0.9, "ok")

    agent = FakeAgent("a", AuthorityLevel.ALERT, frozenset({DecisionAction.ALERT, DecisionAction.DEFER, DecisionAction.ALLOW}), decide)
    out = rig.harness.invoke(agent, request_)
    assert out.decision.action is DecisionAction.DEFER          # safe failure default
    assert out.decision.auto_enforced is False
    kinds = [e.kind for e in rig.audit.security_events]
    assert "tool_not_authorized" in kinds


def test_authorized_tool_call_succeeds(rig, request_):
    calls = []
    rig.registry.register_tool("db", lambda args: calls.append(args) or "row", side_effect="read")
    rig.registry.grant("a", {"db"})

    def decide(_req, tools):
        tools.call("db", {"q": 1})
        return Decision(DecisionAction.ALLOW, 0.95, "ok")

    agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.ALLOW}), decide)
    out = rig.harness.invoke(agent, request_)
    assert calls == [{"q": 1}]
    assert rig.audit.security_events == ()
    assert out.decision.action is DecisionAction.ALLOW


# §9 — No wildcards (§5 T-3) -----------------------------------------------------------------
def test_wildcard_allowlist_rejected(rig):
    with pytest.raises(ToolRegistrationError):
        rig.registry.grant("a", {"*"})


def test_wildcard_tool_name_rejected(rig):
    with pytest.raises(ToolRegistrationError):
        rig.registry.register_tool("db*", lambda args: None)


# §9 — Supervisor holds no tools (§6.3 T-4) --------------------------------------------------
def test_supervisor_with_tools_rejected(rig):
    rig.registry.grant("sup", {"db"})
    sup = FakeAgent("sup", AuthorityLevel.BLOCK, frozenset({DecisionAction.ALLOW}),
                    static_decision(DecisionAction.ALLOW, 0.9))
    w = FakeAgent("w", AuthorityLevel.ALERT, frozenset({DecisionAction.ALERT}),
                  static_decision(DecisionAction.ALERT, 0.9))
    with pytest.raises(ToolRegistrationError):
        SupervisorWorkers(rig.harness, sup, [w])


def test_supervisor_workers_reconciles_to_safest(rig, request_):
    sup = FakeAgent("sup", AuthorityLevel.BLOCK, frozenset({DecisionAction.ALLOW}),
                    static_decision(DecisionAction.ALLOW, 0.9))
    w_allow = FakeAgent("w1", AuthorityLevel.OBSERVE, frozenset({DecisionAction.ALLOW}),
                        static_decision(DecisionAction.ALLOW, 0.9))
    w_block = FakeAgent("w2", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}),
                        static_decision(DecisionAction.BLOCK, 0.97))
    result = SupervisorWorkers(rig.harness, sup, [w_allow, w_block]).run(request_)
    assert result.reconciled_action is DecisionAction.BLOCK   # BLOCK wins the hierarchy
    assert set(result.worker_outputs) == {"w1", "w2"}


# §9 — No self-escalation: authority is static; over-authority action is refused (§3.3) ------
def test_agent_cannot_escalate_authority(rig, request_):
    # An OBSERVE agent tries to emit BLOCK.
    agent = FakeAgent("a", AuthorityLevel.OBSERVE, frozenset({DecisionAction.BLOCK}),
                      static_decision(DecisionAction.BLOCK, 0.99))
    out = rig.harness.invoke(agent, request_)
    assert out.decision.action is DecisionAction.DEFER        # downgraded to safe default
    assert out.decision.auto_enforced is False
    assert any(e.kind == "authority_violation" for e in rig.audit.security_events)


# §9 — Audit append-only + PII-redacted; BLOCK/ALERT carry explanations (§7.3, INV-4) --------
def test_audit_is_append_only_api(rig):
    assert not any(hasattr(rig.audit, n) for n in ("update", "delete", "remove", "clear"))


def test_audit_redacts_pii(rig, request_):
    agent = FakeAgent("a", AuthorityLevel.ALERT, frozenset({DecisionAction.ALERT}),
                      static_decision(DecisionAction.ALERT, 0.9, "contact bob@example.com now"))
    rig.harness.invoke(agent, request_)
    assert "bob@example.com" not in rig.audit.entries[0].rationale
    assert "[REDACTED_EMAIL]" in rig.audit.entries[0].rationale


def test_block_without_rationale_falls_back(rig, request_):
    agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}),
                      static_decision(DecisionAction.BLOCK, 0.99, ""))
    out = rig.harness.invoke(agent, request_)
    assert out.decision.action is DecisionAction.DEFER        # unexplained BLOCK never enforces
    assert out.decision.auto_enforced is False


# §9 — Kill switch: stops autonomy without a deploy (§7.6) -----------------------------------
def test_kill_switch_short_circuits_and_routes(rig, request_):
    def explode(_req, _tools):
        raise AssertionError("agent must NOT run while kill switch is engaged")

    agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}), explode)
    rig.kill.engage()
    out = rig.harness.invoke(agent, request_)
    assert out.decision.action is DecisionAction.DEFER
    assert out.decision.auto_enforced is False
    assert rig.review.items[0].reason == "kill_switch"


# §9 — Safe failure defaults: never fail open (§8) -------------------------------------------
def test_agent_exception_resolves_safely(rig, request_):
    def boom(_req, _tools):
        raise RuntimeError("llm exploded")

    agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}), boom)
    out = rig.harness.invoke(agent, request_)
    assert out.decision.auto_enforced is False
    assert out.decision.confidence <= 0.6
    assert rig.review.items  # routed to a human


def test_reconcile_prefers_block():
    assert reconcile([DecisionAction.ALLOW, DecisionAction.SUGGEST, DecisionAction.BLOCK]) is DecisionAction.BLOCK
    assert reconcile([DecisionAction.ALLOW, DecisionAction.DEFER]) is DecisionAction.DEFER
