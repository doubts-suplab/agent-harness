"""Supervisor + Workers orchestration (spec §6.3, ADR-0007) — the primary multi-step pattern.

A supervisor coordinates worker agents. The supervisor holds NO tool permissions (T-4). Every worker
is invoked through the harness, so each passes the confidence gate and tool registry individually
(O-1). Worker decisions are reconciled via the Decision Hierarchy (spec §3.3).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.agent import Agent
from ..core.errors import ToolRegistrationError
from ..core.harness import Harness
from ..core.model import AgentInput, AgentOutput, DecisionAction, reconcile


@dataclass(frozen=True)
class OrchestrationResult:
    reconciled_action: DecisionAction
    worker_outputs: dict[str, AgentOutput]

    @property
    def any_auto_enforced(self) -> bool:
        return any(o.decision.auto_enforced for o in self.worker_outputs.values())


class SupervisorWorkers:
    """Coordinates worker agents under a tool-less supervisor."""

    def __init__(self, harness: Harness, supervisor: Agent, workers: list[Agent]) -> None:
        if harness.registry.allowlist(supervisor.name):
            raise ToolRegistrationError(
                f"supervisor {supervisor.name!r} MUST hold no tool permissions (spec §6.3 T-4)"
            )
        if not workers:
            raise ValueError("at least one worker agent is required")
        self._harness = harness
        self._supervisor = supervisor
        self._workers = workers

    def run(self, request: AgentInput) -> OrchestrationResult:
        outputs: dict[str, AgentOutput] = {}
        for worker in self._workers:
            outputs[worker.name] = self._harness.invoke(worker, request)
        reconciled = reconcile([o.decision.action for o in outputs.values()])
        return OrchestrationResult(reconciled_action=reconciled, worker_outputs=outputs)
