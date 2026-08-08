"""Parallel Fan-out orchestration (spec §6.2).

Independent worker agents run concurrently over the *same* ``AgentInput``; the harness reconciles
their decisions with the Decision Hierarchy (``BLOCK`` wins, then ``ALERT``, …). Every worker is
invoked through ``Harness.invoke``, so each passes the confidence gate and tool registry individually
(O-1). The aggregation policy is *collect-and-reconcile* — every worker runs and the safest action
wins; no worker's controls are skipped.

Concurrency: workers run on a thread pool. The reference in-memory adapters are concurrency-safe (the
bypass counter is incremented under a lock), so ``confidence_gate_bypass_total`` accumulates correctly.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ..core.agent import Agent
from ..core.harness import Harness
from ..core.model import AgentInput, AgentOutput, DecisionAction, reconcile


@dataclass(frozen=True)
class FanOutResult:
    """The aggregated outcome of a parallel fan-out."""

    reconciled_action: DecisionAction
    worker_outputs: dict[str, AgentOutput]

    @property
    def any_auto_enforced(self) -> bool:
        return any(o.decision.auto_enforced for o in self.worker_outputs.values())


class FanOut:
    """Runs independent workers concurrently over one input, then reconciles their decisions."""

    def __init__(self, harness: Harness, workers: list[Agent], *, max_workers: int | None = None) -> None:
        if not workers:
            raise ValueError("fan-out requires at least one worker agent")
        self._harness = harness
        self._workers = list(workers)
        self._max_workers = max_workers or len(workers)

    def run(self, request: AgentInput) -> FanOutResult:
        # Submit every worker; collect results keyed by worker so the mapping is order-stable
        # regardless of completion order.
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {w.name: pool.submit(self._harness.invoke, w, request) for w in self._workers}
            outputs = {name: future.result() for name, future in futures.items()}

        reconciled = reconcile([o.decision.action for o in outputs.values()])
        return FanOutResult(reconciled_action=reconciled, worker_outputs=outputs)
