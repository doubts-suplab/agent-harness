"""Multi-agent orchestration — the four patterns (spec §6).

Run:  python examples/orchestration.py

Builds three tiny agents and runs them under each orchestration pattern, showing that every pattern
reconciles decisions through the harness (the confidence gate + registry apply to each agent
individually, so ``confidence_gate_bypass_total`` stays 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from agent_harness import (
    AgentInput,
    AuthorityLevel,
    ConsensusRule,
    Debate,
    DecisionAction,
    FanOut,
    Harness,
    Pipeline,
    SupervisorWorkers,
    Decision,
)
from agent_harness.core.agent import ToolInvoker

_ALL = frozenset(
    {DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER}
)


@dataclass
class FixedAgent:
    """An agent that always proposes the same action/confidence (enough to show reconciliation)."""

    name: str
    action: DecisionAction
    confidence: float
    authority_level: AuthorityLevel = AuthorityLevel.BLOCK
    capabilities: frozenset = field(default_factory=lambda: _ALL)

    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        return Decision(self.action, self.confidence, f"{self.name} says {self.action.value}")


def main() -> None:
    harness = Harness()
    request = AgentInput("acme", "alice", context={"task": "review a change"})

    allow = FixedAgent("linter", DecisionAction.ALLOW, 0.95)
    alert = FixedAgent("risk-scanner", DecisionAction.ALERT, 0.9)
    block = FixedAgent("secrets-scanner", DecisionAction.BLOCK, 0.97)

    pipe = Pipeline(harness, [allow, alert, block]).run(request)
    print(f"Pipeline   -> final={pipe.final_action.value} "
          f"(short-circuited at {pipe.short_circuited_at})")

    fan = FanOut(harness, [allow, alert, block]).run(request)
    print(f"Fan-out    -> reconciled={fan.reconciled_action.value} (safest of all workers)")

    debate = Debate(harness, [allow, alert, block], rule=ConsensusRule.MAJORITY).run(request)
    print(f"Debate     -> consensus={debate.consensus_action.value} "
          f"(rule=MAJORITY, tie={debate.tie})")

    # A supervisor holds no tools; it plans, then delegates to the workers.
    supervisor = FixedAgent("supervisor", DecisionAction.ALLOW, 0.9)
    sup = SupervisorWorkers(harness, supervisor, [allow, alert, block]).run(request)
    print(f"Supervisor -> reconciled={sup.reconciled_action.value} "
          f"delegated={list(sup.delegated)}")

    bypasses = harness.observability.counter("confidence_gate_bypass_total")
    print(f"\nconfidence_gate_bypass_total = {bypasses}  (must be 0)")


if __name__ == "__main__":
    main()
