"""Human-review SLA monitor (spec §7.4).

Sweeps a review queue for items past their SLA deadline and emits a breach counter through the
ObservabilityPort. Each breached item is counted at most once, so repeated sweeps are idempotent.
This is the enforcement/monitoring hook the spec calls for; escalation policy (paging, reassignment)
is the integrator's concern and sits above this signal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..ports.governance import ObservabilityPort

# Emitted once per review item that breaches its SLA (spec §7.4).
HUMAN_REVIEW_SLA_BREACH = "human_review_sla_breach_total"


class _OverdueSource(Protocol):
    def overdue(self, now: datetime | None = ...) -> tuple: ...


class SlaMonitor:
    """Counts SLA breaches in a human-review queue, idempotently across sweeps."""

    def __init__(self, queue: _OverdueSource, observability: ObservabilityPort) -> None:
        self._queue = queue
        self._obs = observability
        self._counted: set[int] = set()

    def sweep(self, now: datetime | None = None) -> tuple:
        """Return currently-overdue items; increment the breach counter for newly-breached ones."""
        breached = self._queue.overdue(now)
        for q in breached:
            if q.id not in self._counted:
                self._counted.add(q.id)
                self._obs.increment_counter(HUMAN_REVIEW_SLA_BREACH)
        return breached

    @property
    def breach_count(self) -> int:
        return len(self._counted)
