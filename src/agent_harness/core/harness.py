"""The Harness — safe, governed invocation of a single agent (spec §2–§8).

Every agent invocation flows through here. The harness validates scope, honours the kill switch,
runs the agent with a registry-enforced tool invoker, applies the confidence gate, routes
non-enforcing decisions to human review, and records audit + observability. On any failure it
resolves to a safe, non-enforcing decision (spec §8) — it never fails open.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ..ports.governance import (
    AuditEntry,
    AuditPort,
    HumanReviewPort,
    InvocationMetric,
    KillSwitchPort,
    ObservabilityPort,
    ReviewItem,
    SecurityEvent,
)
from .agent import Agent
from .errors import ToolNotAuthorizedError, UnscopedInvocationError
from .failure import FailureMode, default_for
from .gate import ConfidenceGate
from .model import (
    AgentInput,
    AgentOutput,
    Decision,
    DecisionAction,
    action_within_authority,
)
from .registry import ToolRegistry

BYPASS_COUNTER = "confidence_gate_bypass_total"

# spec §7.4 SLAs (seconds): BLOCK-level 1h, everything else 4h.
_SLA_BLOCK = 3600
_SLA_DEFAULT = 14400


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _BoundInvoker:
    """A ToolInvoker scoped to one agent + request; enforces the registry and records violations."""

    def __init__(self, harness: "Harness", agent_name: str, request: AgentInput) -> None:
        self._h = harness
        self._agent = agent_name
        self._request = request

    def call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        try:
            return self._h.registry.invoke(self._agent, tool_name, arguments)
        except ToolNotAuthorizedError as exc:
            self._h.audit.record_security_event(
                SecurityEvent(
                    agent_name=self._agent,
                    tenant_id=self._request.tenant_id,
                    kind="tool_not_authorized",
                    detail=f"tool={tool_name}",
                    correlation_id=self._request.correlation_id,
                    recorded_at=_now(),
                )
            )
            raise


class Harness:
    """Wraps agent execution with the harness's controls."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        audit: AuditPort | None = None,
        human_review: HumanReviewPort | None = None,
        observability: ObservabilityPort | None = None,
        kill_switch: KillSwitchPort | None = None,
        gate: ConfidenceGate | None = None,
    ) -> None:
        # Lazily import the in-memory reference adapters so the core stays import-pure (INV-5):
        # nothing here is imported at module load; only when a port is left unset.
        if audit is None or human_review is None or observability is None or kill_switch is None:
            from ..adapters.inmemory import (
                InMemoryAudit,
                InMemoryHumanReview,
                InMemoryKillSwitch,
                InMemoryObservability,
            )

            audit = audit or InMemoryAudit()
            human_review = human_review or InMemoryHumanReview()
            observability = observability or InMemoryObservability()
            kill_switch = kill_switch or InMemoryKillSwitch()

        self.registry = registry or ToolRegistry()
        self.audit = audit
        self.human_review = human_review
        self.observability = observability
        self.kill_switch = kill_switch
        self.gate = gate or ConfidenceGate()

    # -- public API ------------------------------------------------------
    def invoke(self, agent: Agent, request: AgentInput) -> AgentOutput:
        # Scope is validated, never defaulted (spec §2.1).
        if not request.is_scoped():
            raise UnscopedInvocationError("AgentInput MUST carry non-empty tenantId and userId")

        started = time.perf_counter()

        # Kill switch: short-circuit before any tool side effect; route to human review (spec §7.6).
        if self.kill_switch.is_engaged():
            decision = Decision(
                action=DecisionAction.DEFER,
                confidence=0.0,
                rationale="kill switch engaged — routed to human review",
                auto_enforced=False,
            )
            return self._finalize(agent, request, decision, started, reason="kill_switch")

        decision, reason = self._run_agent(agent, request)
        return self._finalize(agent, request, decision, started, reason=reason)

    # -- internals -------------------------------------------------------
    def _run_agent(self, agent: Agent, request: AgentInput) -> tuple[Decision, str | None]:
        invoker = _BoundInvoker(self, agent.name, request)
        try:
            decision = agent.run(request, invoker)
        except ToolNotAuthorizedError:
            return default_for(FailureMode.TOOL_FAILURE, "unauthorized tool call"), "failure"
        except Exception as exc:  # any agent/LLM failure resolves safely (spec §8)
            return default_for(FailureMode.BAD_OUTPUT, type(exc).__name__), "failure"

        # The agent must not set auto_enforced; the harness owns it (spec §2.2). Reset defensively.
        decision.auto_enforced = False

        # Undeclared action → contract violation → safe default (spec §10 capability declaration).
        if decision.action not in agent.capabilities:
            return default_for(FailureMode.BAD_OUTPUT, f"undeclared action {decision.action.value}"), "failure"

        # Out-of-authority action → safe default + security-relevant (spec §3.3).
        if not action_within_authority(decision.action, agent.authority_level):
            self.audit.record_security_event(
                SecurityEvent(
                    agent_name=agent.name,
                    tenant_id=request.tenant_id,
                    kind="authority_violation",
                    detail=f"action={decision.action.value} authority={agent.authority_level.name}",
                    correlation_id=request.correlation_id,
                    recorded_at=_now(),
                )
            )
            return default_for(FailureMode.OUT_OF_AUTHORITY, decision.action.value), "failure"

        # Shape validation (confidence range, rationale on BLOCK/ALERT).
        try:
            decision.validate()
        except ValueError as exc:
            return default_for(FailureMode.BAD_OUTPUT, str(exc)), "failure"

        return decision, None

    def _finalize(
        self,
        agent: Agent,
        request: AgentInput,
        decision: Decision,
        started: float,
        *,
        reason: str | None,
    ) -> AgentOutput:
        # The gate is the ONLY place auto_enforced is decided (spec §4, INV-1).
        self.gate.evaluate(decision, agent.authority_level)

        # Defensive bypass detection — must never fire in a correct system (spec §4.2).
        if self.gate.is_bypass(decision, agent.authority_level):
            self.observability.increment_counter(BYPASS_COUNTER)
            decision.auto_enforced = False  # never let a bypass stand

        outcome = "auto-enforced" if decision.auto_enforced else "human-review"

        if not decision.auto_enforced:
            self.human_review.enqueue(
                ReviewItem(
                    agent_name=agent.name,
                    request=request,
                    decision=decision,
                    reason=reason or self._review_reason(decision),
                    sla_seconds=_SLA_BLOCK if decision.action is DecisionAction.BLOCK else _SLA_DEFAULT,
                    enqueued_at=_now(),
                )
            )

        self.audit.record(
            AuditEntry(
                agent_name=agent.name,
                tenant_id=request.tenant_id,
                action=decision.action.value,
                confidence=decision.confidence,
                auto_enforced=decision.auto_enforced,
                rationale=decision.rationale,
                outcome=outcome,
                correlation_id=request.correlation_id,
                recorded_at=_now(),
            )
        )

        duration_ms = (time.perf_counter() - started) * 1000.0
        self.observability.emit(
            InvocationMetric(
                agent_name=agent.name,
                action=decision.action.value,
                confidence=decision.confidence,
                duration_ms=duration_ms,
                outcome=outcome,
                correlation_id=request.correlation_id,
            )
        )
        return AgentOutput.now(decision, agent.name)

    @staticmethod
    def _review_reason(decision: Decision) -> str:
        if decision.action is DecisionAction.DEFER:
            return "defer"
        if decision.action is DecisionAction.SUGGEST:
            return "suggest"
        return "low_confidence"
