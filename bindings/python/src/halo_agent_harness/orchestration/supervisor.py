"""Supervisor + Workers orchestration (spec §6.3, ADR-0007) — the primary multi-step pattern.

A supervisor coordinates worker agents. The supervisor holds NO tool permissions (T-4). The run has
two phases:

1. **Planning turn.** The supervisor is invoked *through the harness* (`Harness.invoke`), so its
   planning decision passes the confidence gate, kill switch, and audit like any other invocation
   (O-1) — it just cannot touch tools. If the supervisor's decision is ``BLOCK`` or ``DEFER`` it
   **halts delegation**: no workers run. Otherwise the supervisor may select which workers to engage.
2. **Delegation.** Selected workers are each invoked through the harness (gate + registry individually),
   and their decisions are reconciled via the Decision Hierarchy (spec §3.3).

Worker selection is optional: a supervisor that also implements :class:`Planner` chooses a subset of
workers; a plain supervisor delegates to all of them (backwards-compatible).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..core.agent import Agent
from ..core.errors import ToolRegistrationError
from ..core.harness import Harness
from ..core.model import AgentInput, AgentOutput, DecisionAction, reconcile

# A supervisor decision in this set stops the orchestration before any worker runs (spec §6.3).
_HALT = frozenset({DecisionAction.BLOCK, DecisionAction.DEFER})


@runtime_checkable
class Planner(Protocol):
    """Optional supervisor capability: choose which workers to delegate to (spec §6.3).

    Planning is a pure coordination step — it selects names, it does not act — so it needs no tools.
    """

    def plan(self, request: AgentInput, worker_names: list[str]) -> list[str]:
        """Return the subset of ``worker_names`` to engage for this request."""
        ...


@dataclass(frozen=True)
class OrchestrationResult:
    reconciled_action: DecisionAction
    worker_outputs: dict[str, AgentOutput]
    supervisor_output: AgentOutput | None = None
    delegated: tuple[str, ...] = ()
    halted: bool = False

    @property
    def any_auto_enforced(self) -> bool:
        return any(o.decision.auto_enforced for o in self.worker_outputs.values())


class SupervisorWorkers:
    """Coordinates worker agents under a tool-less supervisor with a real planning turn."""

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
        # Phase 1 — governed planning turn. The supervisor reasons about the task under the harness.
        supervisor_output = self._harness.invoke(self._supervisor, request)
        plan_action = supervisor_output.decision.action

        # A halting supervisor decision stops the orchestration before any worker side effect.
        if plan_action in _HALT:
            return OrchestrationResult(
                reconciled_action=plan_action,
                worker_outputs={},
                supervisor_output=supervisor_output,
                delegated=(),
                halted=True,
            )

        # Phase 2 — delegation. Select workers (all, unless the supervisor is a Planner).
        workers_by_name = {w.name: w for w in self._workers}
        selected = self._select(request, list(workers_by_name))

        outputs: dict[str, AgentOutput] = {}
        for name in selected:
            outputs[name] = self._harness.invoke(workers_by_name[name], request)

        # Reconcile the workers that acted; with no delegation, the supervisor's own action stands.
        actions = [o.decision.action for o in outputs.values()] or [plan_action]
        reconciled = reconcile(actions)
        return OrchestrationResult(
            reconciled_action=reconciled,
            worker_outputs=outputs,
            supervisor_output=supervisor_output,
            delegated=tuple(selected),
            halted=False,
        )

    def _select(self, request: AgentInput, worker_names: list[str]) -> list[str]:
        if isinstance(self._supervisor, Planner):
            chosen = self._supervisor.plan(request, list(worker_names))
            # Constrain to real workers; the supervisor cannot invent or reorder beyond the roster.
            return [n for n in chosen if n in worker_names]
        return worker_names
