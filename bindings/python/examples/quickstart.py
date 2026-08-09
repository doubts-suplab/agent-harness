"""Quickstart — invoke a governed agent through the harness.

Run:  python examples/quickstart.py

Shows the two things the harness guarantees: (1) a high-confidence decision within authority
auto-enforces; (2) a low-confidence decision is routed to human review with auto_enforced=False —
and the agent never gets to decide that for itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from halo_agent_harness import (
    AgentInput,
    AuthorityLevel,
    Decision,
    DecisionAction,
    Harness,
)
from halo_agent_harness.adapters import InMemoryAudit, InMemoryHumanReview, InMemoryObservability
from halo_agent_harness.core.agent import ToolInvoker


@dataclass
class PolicyAgent:
    """A tiny BLOCK-authority agent: blocks when it is confident, defers otherwise."""

    name: str = "policy-agent"
    authority_level: AuthorityLevel = AuthorityLevel.BLOCK
    capabilities: frozenset[DecisionAction] = frozenset({DecisionAction.BLOCK, DecisionAction.DEFER, DecisionAction.ALLOW})

    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        risk = float(request.context.get("risk", 0.0))
        if risk >= 0.9:
            return Decision(DecisionAction.BLOCK, confidence=risk, rationale=f"risk {risk} exceeds policy")
        return Decision(DecisionAction.ALLOW, confidence=0.6, rationale="within tolerance but unsure")


def main() -> None:
    audit, review, obs = InMemoryAudit(), InMemoryHumanReview(), InMemoryObservability()
    harness = Harness(audit=audit, human_review=review, observability=obs)
    agent = PolicyAgent()

    high = harness.invoke(agent, AgentInput("acme", "alice", context={"risk": 0.97}))
    print(f"high risk  -> action={high.decision.action.value} "
          f"auto_enforced={high.decision.auto_enforced}")

    low = harness.invoke(agent, AgentInput("acme", "bob", context={"risk": 0.2}))
    print(f"low  conf  -> action={low.decision.action.value} "
          f"auto_enforced={low.decision.auto_enforced} (routed to human)")

    print(f"\naudit entries: {len(audit.entries)} | review queue: {len(review.items)} "
          f"| gate bypasses: {obs.counter('confidence_gate_bypass_total')}")


if __name__ == "__main__":
    main()
