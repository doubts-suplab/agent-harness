"""Pluggable redaction tests (spec §7.3)."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_harness.adapters import (
    DEFAULT_STRATEGY,
    InMemoryAudit,
    RedactionStrategy,
    redact,
)
from agent_harness.ports.governance import AuditEntry

_NOW = datetime(2026, 8, 8, tzinfo=timezone.utc)


def test_default_strategy_covers_common_pii():
    assert "bob@example.com" not in redact("mail bob@example.com")
    assert "[REDACTED_EMAIL]" in redact("mail bob@example.com")
    assert "[REDACTED_CARD]" in redact("card 4111 1111 1111 1111")
    assert "[REDACTED_SSN]" in redact("ssn 123-45-6789")


def test_strategy_is_callable():
    assert DEFAULT_STRATEGY("mail bob@example.com") == redact("mail bob@example.com")


def test_with_rule_extends_without_mutating_the_base():
    custom = DEFAULT_STRATEGY.with_rule(r"ACME-\d+", "[REDACTED_CASEID]")
    assert custom("case ACME-42 for bob@example.com") == "case [REDACTED_CASEID] for [REDACTED_EMAIL]"
    # The base strategy is unchanged (immutable).
    assert "ACME-42" in redact("case ACME-42")


def test_empty_strategy_redacts_nothing():
    passthrough = RedactionStrategy(rules=())
    assert passthrough("bob@example.com") == "bob@example.com"


def test_audit_uses_pluggable_redactor():
    audit = InMemoryAudit(redactor=RedactionStrategy().with_rule(r"topsecret", "[X]"))
    audit.record(AuditEntry("a", "t1", "ALERT", 0.9, False, "topsecret and bob@example.com",
                            "human-review", None, _NOW))
    rationale = audit.entries[0].rationale
    assert "[X]" in rationale
    assert "[REDACTED_EMAIL]" in rationale
