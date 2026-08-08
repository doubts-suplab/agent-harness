"""Core domain model — the agent I/O envelope and the two-axis authority/decision model.

Implements harness-protocol.md §2 (envelope) and §3 (authority + decision). This module is
framework-free and dependency-free (ADR-0005, INV-5).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class AuthorityLevel(enum.IntEnum):
    """An agent's static capability ceiling (spec §3.1). Ordered: higher = more authority.

    MUST NOT change at runtime (no self-escalation, INV-3).
    """

    OBSERVE = 1
    SUGGEST = 2
    ALERT = 3
    RATE_LIMIT = 4
    BLOCK = 5


class DecisionAction(enum.Enum):
    """The dynamic outcome of a single invocation (spec §3.2)."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ALERT = "ALERT"
    SUGGEST = "SUGGEST"
    DEFER = "DEFER"


# §3.3 binding rule: the minimum authority a DecisionAction requires.
_ACTION_MIN_AUTHORITY: dict[DecisionAction, AuthorityLevel] = {
    DecisionAction.ALLOW: AuthorityLevel.OBSERVE,   # no external effect
    DecisionAction.DEFER: AuthorityLevel.OBSERVE,   # routes to a human; no autonomous effect
    DecisionAction.SUGGEST: AuthorityLevel.SUGGEST,
    DecisionAction.ALERT: AuthorityLevel.ALERT,
    DecisionAction.BLOCK: AuthorityLevel.BLOCK,
}

# §3.3 Decision Hierarchy for reconciling multiple agents' decisions.
# BLOCK > RATE_LIMIT > ALERT > SUGGEST > DEFER > ALLOW. RATE_LIMIT is an authority level, not a
# DecisionAction, so over the action set the effective precedence is:
_ACTION_PRECEDENCE: dict[DecisionAction, int] = {
    DecisionAction.BLOCK: 5,
    DecisionAction.ALERT: 3,
    DecisionAction.SUGGEST: 2,
    DecisionAction.DEFER: 1,
    DecisionAction.ALLOW: 0,
}


def min_authority_for(action: DecisionAction) -> AuthorityLevel:
    """The minimum authority level required to emit ``action`` (spec §3.3)."""
    return _ACTION_MIN_AUTHORITY[action]


def action_within_authority(action: DecisionAction, authority: AuthorityLevel) -> bool:
    """True if an agent at ``authority`` is permitted to emit ``action`` (spec §3.3)."""
    return authority >= _ACTION_MIN_AUTHORITY[action]


def action_precedence(action: DecisionAction) -> int:
    """The Decision-Hierarchy precedence of an action (§3.3): higher = safer/stricter."""
    return _ACTION_PRECEDENCE[action]


def reconcile(actions: list[DecisionAction]) -> DecisionAction:
    """Reconcile competing decisions toward the safer action (spec §3.3, §6.2)."""
    if not actions:
        raise ValueError("cannot reconcile an empty list of actions")
    return max(actions, key=lambda a: _ACTION_PRECEDENCE[a])


@dataclass(frozen=True)
class AgentInput:
    """One invocation's input (spec §2.1). ``tenantId``/``userId`` are the multi-tenancy boundary."""

    tenant_id: str
    user_id: str
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_scoped(self) -> bool:
        """True if tenant and user scope are both present and non-empty (spec §2.1)."""
        return bool(self.tenant_id) and bool(self.user_id)

    @property
    def correlation_id(self) -> str | None:
        """Correlation/trace id to propagate into every port call (spec §7.5)."""
        cid = self.metadata.get("correlationId") or self.metadata.get("correlation_id")
        return str(cid) if cid is not None else None


@dataclass
class Decision:
    """The outcome an agent proposes; ``auto_enforced`` is owned by the harness (spec §2.2, §4).

    An agent MUST NOT set ``auto_enforced``; the harness overwrites it via the confidence gate.
    """

    action: DecisionAction
    confidence: float
    rationale: str
    auto_enforced: bool = False

    def validate(self) -> None:
        """Protocol-level validation of the decision shape (spec §2.2)."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence {self.confidence!r} out of range [0.0, 1.0]")
        if self.action in (DecisionAction.BLOCK, DecisionAction.ALERT) and not self.rationale.strip():
            raise ValueError(f"{self.action.value} decisions MUST carry a human-readable rationale")


@dataclass(frozen=True)
class AgentOutput:
    """One invocation's output envelope (spec §2.2)."""

    decision: Decision
    agent_name: str
    executed_at: datetime

    @staticmethod
    def now(decision: Decision, agent_name: str) -> "AgentOutput":
        return AgentOutput(decision=decision, agent_name=agent_name, executed_at=datetime.now(timezone.utc))
