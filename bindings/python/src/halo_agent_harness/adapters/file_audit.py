"""Durable, append-only file AuditPort (spec §7.3).

Writes one JSON object per line (JSONL) to a file, in append mode. There is **no** update or delete
API — the log is append-only by construction (INV-4). PII is redacted before every write. This is a
minimal, dependency-free durable adapter; a JDBC / object-store adapter follows the same contract.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..ports.governance import AuditEntry, SecurityEvent
from .inmemory import redact

_DECISION = "decision"
_SECURITY = "security_event"


class FileAudit:
    """Append-only JSONL audit log. Implements ``AuditPort``; adds read-back helpers for inspection."""

    def __init__(self, path: str | Path, *, redactor: Callable[[str], str] = redact) -> None:
        self._path = Path(path)
        self._redact = redactor
        self._lock = threading.Lock()
        # Ensure the parent directory exists; create the file lazily on first append.
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # -- AuditPort ------------------------------------------------------
    def record(self, entry: AuditEntry) -> None:
        self._append(
            {
                "type": _DECISION,
                "agent_name": entry.agent_name,
                "tenant_id": entry.tenant_id,
                "action": entry.action,
                "confidence": entry.confidence,
                "auto_enforced": entry.auto_enforced,
                "rationale": self._redact(entry.rationale),
                "outcome": entry.outcome,
                "correlation_id": entry.correlation_id,
                "recorded_at": entry.recorded_at.isoformat(),
            }
        )

    def record_security_event(self, event: SecurityEvent) -> None:
        self._append(
            {
                "type": _SECURITY,
                "agent_name": event.agent_name,
                "tenant_id": event.tenant_id,
                "kind": event.kind,
                "detail": self._redact(event.detail),
                "correlation_id": event.correlation_id,
                "recorded_at": event.recorded_at.isoformat(),
            }
        )

    # -- inspection (read-back) -----------------------------------------
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(
            AuditEntry(
                agent_name=r["agent_name"],
                tenant_id=r["tenant_id"],
                action=r["action"],
                confidence=r["confidence"],
                auto_enforced=r["auto_enforced"],
                rationale=r["rationale"],
                outcome=r["outcome"],
                correlation_id=r["correlation_id"],
                recorded_at=datetime.fromisoformat(r["recorded_at"]),
            )
            for r in self._read()
            if r.get("type") == _DECISION
        )

    def security_events(self) -> tuple[SecurityEvent, ...]:
        return tuple(
            SecurityEvent(
                agent_name=r["agent_name"],
                tenant_id=r["tenant_id"],
                kind=r["kind"],
                detail=r["detail"],
                correlation_id=r["correlation_id"],
                recorded_at=datetime.fromisoformat(r["recorded_at"]),
            )
            for r in self._read()
            if r.get("type") == _SECURITY
        )

    @property
    def path(self) -> Path:
        return self._path

    # -- internals ------------------------------------------------------
    def _append(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
