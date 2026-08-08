"""In-memory reference adapters (spec §7). For tests, local runs, and as an adapter template.

Production deployments supply their own adapters (Postgres audit, a real queue, OpenTelemetry, …).
These implement the port Protocols and depend on the core — never the reverse (ADR-0005).
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, replace

from datetime import datetime, timezone

from ..ports.governance import (
    AuditEntry,
    HumanReviewPort,
    InvocationMetric,
    OverrideRecord,
    ReviewItem,
    SecurityEvent,
)

# spec §7.3: redact PII before any audit write. Order matters (JWT/card before generic digits).
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[REDACTED_JWT]"),
    (re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b(?:\+?\d[\d -]{8,}\d)\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b(?:sk|pk|ghp|xox[baprs])[-_][A-Za-z0-9]{8,}\b"), "[REDACTED_KEY]"),
]


def redact(text: str) -> str:
    """Redact common PII/secret patterns (spec §7.3). Zero PII in logs is a P1 condition."""
    out = text
    for pattern, replacement in _PII_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


class InMemoryAudit:
    """Append-only audit log (spec §7.3). No update/delete API is exposed; PII is redacted on write."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._security_events: list[SecurityEvent] = []

    def record(self, entry: AuditEntry) -> None:
        self._entries.append(replace(entry, rationale=redact(entry.rationale)))

    def record_security_event(self, event: SecurityEvent) -> None:
        self._security_events.append(replace(event, detail=redact(event.detail)))

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    @property
    def security_events(self) -> tuple[SecurityEvent, ...]:
        return tuple(self._security_events)


@dataclass
class QueuedReview:
    """A queued review item with a stable id and resolution state (spec §7.4)."""

    id: int
    item: ReviewItem
    resolved: bool = False
    override: OverrideRecord | None = None


class InMemoryHumanReview(HumanReviewPort):
    """Human-review queue with SLA tracking and an audited override endpoint (spec §7.4).

    Beyond ``enqueue``, it assigns each item a stable id, distinguishes pending vs resolved,
    exposes overdue (SLA-breached) items for a monitor to sweep, and records human overrides.
    """

    def __init__(self) -> None:
        self._queue: list[QueuedReview] = []
        self._next_id = 0

    def enqueue(self, item: ReviewItem) -> int:
        review_id = self._next_id
        self._next_id += 1
        self._queue.append(QueuedReview(id=review_id, item=item))
        return review_id

    @property
    def items(self) -> tuple[ReviewItem, ...]:
        return tuple(q.item for q in self._queue)

    @property
    def queued(self) -> tuple[QueuedReview, ...]:
        return tuple(self._queue)

    def pending(self) -> tuple[QueuedReview, ...]:
        return tuple(q for q in self._queue if not q.resolved)

    def overdue(self, now: datetime | None = None) -> tuple[QueuedReview, ...]:
        """Pending items whose SLA deadline has passed (spec §7.4)."""
        moment = now or datetime.now(timezone.utc)
        return tuple(q for q in self.pending() if q.item.is_overdue(moment))

    def resolve(self, review_id: int, reviewer: str, outcome: str) -> OverrideRecord:
        """Record a human override of a queued decision (spec §7.4 — overrides are audited).

        Returns the ``OverrideRecord`` so the caller can write it to the AuditPort.
        """
        q = self._find(review_id)
        if q.resolved:
            raise ValueError(f"review {review_id} is already resolved")
        record = OverrideRecord(
            review_id=review_id,
            agent_name=q.item.agent_name,
            tenant_id=q.item.request.tenant_id,
            reviewer=reviewer,
            outcome=outcome,
            resolved_at=datetime.now(timezone.utc),
        )
        q.resolved = True
        q.override = record
        return record

    def _find(self, review_id: int) -> QueuedReview:
        for q in self._queue:
            if q.id == review_id:
                return q
        raise KeyError(f"no review with id {review_id}")


class InMemoryObservability:
    def __init__(self) -> None:
        self._metrics: list[InvocationMetric] = []
        self._counters: dict[str, int] = {}
        # Counter increments are a read-modify-write; guard them so concurrent fan-out workers
        # (spec §6.2) accumulate the bypass counter safely. list.append is atomic under the GIL.
        self._lock = threading.Lock()

    def emit(self, metric: InvocationMetric) -> None:
        self._metrics.append(metric)

    def increment_counter(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    @property
    def metrics(self) -> tuple[InvocationMetric, ...]:
        return tuple(self._metrics)


class InMemoryKillSwitch:
    def __init__(self, engaged: bool = False) -> None:
        self._engaged = engaged

    def is_engaged(self) -> bool:
        return self._engaged

    def engage(self) -> None:
        self._engaged = True

    def disengage(self) -> None:
        self._engaged = False
