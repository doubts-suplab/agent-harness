"""Governance ports — audit, human review, observability, memory, kill switch, policy (spec §7).

All are Protocols; concrete adapters live at the edge and depend on this core, never the reverse
(ADR-0005). Data types carried across the ports are defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from ..core.model import AgentInput, Decision


# ---------------------------------------------------------------------------
# Audit (spec §7.3) — append-only, PII-redacted
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AuditEntry:
    agent_name: str
    tenant_id: str
    action: str
    confidence: float
    auto_enforced: bool
    rationale: str
    outcome: str            # "auto-enforced" | "human-review"
    correlation_id: str | None
    recorded_at: datetime


@dataclass(frozen=True)
class SecurityEvent:
    agent_name: str
    tenant_id: str
    kind: str               # e.g. "tool_not_authorized"
    detail: str
    correlation_id: str | None
    recorded_at: datetime


@runtime_checkable
class AuditPort(Protocol):
    """Append-only audit log. Implementations MUST NOT update or delete, and MUST redact PII."""

    def record(self, entry: AuditEntry) -> None: ...
    def record_security_event(self, event: SecurityEvent) -> None: ...


# ---------------------------------------------------------------------------
# Human review queue (spec §7.4)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ReviewItem:
    agent_name: str
    request: AgentInput
    decision: Decision
    reason: str             # why it was routed (low_confidence | defer | suggest | kill_switch | failure)
    sla_seconds: int
    enqueued_at: datetime

    @property
    def deadline(self) -> datetime:
        """When this item breaches its SLA (spec §7.4)."""
        return self.enqueued_at + timedelta(seconds=self.sla_seconds)

    def is_overdue(self, now: datetime) -> bool:
        return now > self.deadline


@dataclass(frozen=True)
class OverrideRecord:
    """A human override of a queued decision — itself auditable (spec §7.4)."""

    review_id: int
    agent_name: str
    tenant_id: str
    reviewer: str
    outcome: str            # the human's resolution, e.g. "approved" | "rejected" | "amended"
    resolved_at: datetime


@runtime_checkable
class HumanReviewPort(Protocol):
    """Queue for decisions that must reach a human, with an SLA per item."""

    def enqueue(self, item: ReviewItem) -> None: ...


# ---------------------------------------------------------------------------
# Observability (spec §7.5, §4.2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class InvocationMetric:
    agent_name: str
    action: str
    confidence: float
    duration_ms: float
    outcome: str
    correlation_id: str | None


@runtime_checkable
class ObservabilityPort(Protocol):
    """Per-invocation metrics + counters. MUST expose ``confidence_gate_bypass_total`` (must stay 0)."""

    def emit(self, metric: InvocationMetric) -> None: ...
    def increment_counter(self, name: str, value: int = 1) -> None: ...


# ---------------------------------------------------------------------------
# Kill switch (spec §7.6)
# ---------------------------------------------------------------------------
@runtime_checkable
class KillSwitchPort(Protocol):
    """System-wide stop without a code deploy. When engaged, nothing auto-enforces."""

    def is_engaged(self) -> bool: ...


# ---------------------------------------------------------------------------
# Memory (spec §7) — always scoped by tenant
# ---------------------------------------------------------------------------
@runtime_checkable
class MemoryPort(Protocol):
    def read(self, tenant_id: str, user_id: str, key: str) -> Any | None: ...
    def write(self, tenant_id: str, user_id: str, key: str, value: Any) -> None: ...


# ---------------------------------------------------------------------------
# Policy (spec §7) — evaluate authority/action against immutable rules (optional; default allow)
# ---------------------------------------------------------------------------
@runtime_checkable
class PolicyPort(Protocol):
    def permits(self, agent_name: str, action: str, tenant_id: str) -> bool: ...
