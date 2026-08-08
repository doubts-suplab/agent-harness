"""Durable append-only file AuditPort tests (spec §7.3)."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_harness.adapters import FileAudit
from agent_harness.ports.governance import AuditEntry, SecurityEvent

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _entry(rationale="ok", agent="a", tenant="t1", action="ALERT"):
    return AuditEntry(
        agent_name=agent, tenant_id=tenant, action=action, confidence=0.9,
        auto_enforced=False, rationale=rationale, outcome="human-review",
        correlation_id="corr-1", recorded_at=_NOW,
    )


def _event(detail="tool=db", kind="tool_not_authorized"):
    return SecurityEvent(agent_name="a", tenant_id="t1", kind=kind, detail=detail,
                         correlation_id="corr-1", recorded_at=_NOW)


def test_records_round_trip_through_the_file(tmp_path):
    audit = FileAudit(tmp_path / "audit.jsonl")
    audit.record(_entry(action="BLOCK"))
    audit.record_security_event(_event())

    entries = audit.entries()
    events = audit.security_events()
    assert len(entries) == 1 and entries[0].action == "BLOCK"
    assert len(events) == 1 and events[0].kind == "tool_not_authorized"
    assert entries[0].recorded_at == _NOW  # datetime survives the round trip


def test_is_append_only_across_instances(tmp_path):
    path = tmp_path / "audit.jsonl"
    FileAudit(path).record(_entry(rationale="first"))
    # A fresh adapter over the same file appends, never truncates.
    second = FileAudit(path)
    second.record(_entry(rationale="second"))
    assert [e.rationale for e in second.entries()] == ["first", "second"]
    assert path.read_text().count("\n") == 2  # one line per record


def test_pii_is_redacted_before_write(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit = FileAudit(path)
    audit.record(_entry(rationale="email bob@example.com now"))
    audit.record_security_event(_event(detail="card 4111 1111 1111 1111"))

    raw = path.read_text()
    assert "bob@example.com" not in raw
    assert "[REDACTED_EMAIL]" in raw
    assert "4111 1111 1111 1111" not in raw
    assert "[REDACTED_CARD]" in raw


def test_no_update_or_delete_api_is_exposed(tmp_path):
    audit = FileAudit(tmp_path / "audit.jsonl")
    for name in ("update", "delete", "remove", "truncate", "clear"):
        assert not hasattr(audit, name)


def test_empty_log_reads_as_empty(tmp_path):
    audit = FileAudit(tmp_path / "audit.jsonl")
    assert audit.entries() == ()
    assert audit.security_events() == ()
