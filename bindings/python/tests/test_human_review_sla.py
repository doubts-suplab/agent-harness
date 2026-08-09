"""Human-review SLA enforcement + monitoring tests (spec §7.4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from halo_agent_harness import AgentInput, Decision, DecisionAction
from halo_agent_harness.adapters import (
    HUMAN_REVIEW_SLA_BREACH,
    InMemoryHumanReview,
    InMemoryObservability,
    SlaMonitor,
)
from halo_agent_harness.ports.governance import ReviewItem

_T0 = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _item(sla_seconds=3600, enqueued_at=_T0, agent="a", tenant="t1"):
    return ReviewItem(
        agent_name=agent,
        request=AgentInput(tenant_id=tenant, user_id="u1"),
        decision=Decision(DecisionAction.DEFER, 0.5, "review me"),
        reason="defer",
        sla_seconds=sla_seconds,
        enqueued_at=enqueued_at,
    )


def test_review_item_deadline_and_overdue():
    item = _item(sla_seconds=3600, enqueued_at=_T0)
    assert item.deadline == _T0 + timedelta(hours=1)
    assert item.is_overdue(_T0 + timedelta(minutes=59)) is False
    assert item.is_overdue(_T0 + timedelta(hours=2)) is True


def test_enqueue_assigns_ids_and_pending():
    q = InMemoryHumanReview()
    id0 = q.enqueue(_item())
    id1 = q.enqueue(_item())
    assert (id0, id1) == (0, 1)
    assert len(q.pending()) == 2
    assert len(q.items) == 2  # backwards-compatible view


def test_resolve_marks_resolved_and_returns_audited_override():
    q = InMemoryHumanReview()
    rid = q.enqueue(_item(agent="gov", tenant="acme"))
    record = q.resolve(rid, reviewer="alice", outcome="approved")
    assert record.review_id == rid
    assert record.reviewer == "alice"
    assert record.outcome == "approved"
    assert record.agent_name == "gov"
    assert record.tenant_id == "acme"
    assert q.pending() == ()  # nothing left pending


def test_resolve_unknown_or_double_raises():
    q = InMemoryHumanReview()
    rid = q.enqueue(_item())
    with pytest.raises(KeyError):
        q.resolve(999, "bob", "approved")
    q.resolve(rid, "bob", "approved")
    with pytest.raises(ValueError):
        q.resolve(rid, "bob", "approved")  # already resolved


def test_overdue_sweep_finds_only_breached_pending_items():
    q = InMemoryHumanReview()
    q.enqueue(_item(sla_seconds=3600, enqueued_at=_T0))          # id 0 — breaches at T0+1h
    q.enqueue(_item(sla_seconds=14400, enqueued_at=_T0))         # id 1 — breaches at T0+4h
    now = _T0 + timedelta(hours=2)
    overdue = q.overdue(now)
    assert [o.id for o in overdue] == [0]  # only the 1h-SLA item is overdue


def test_sla_monitor_emits_breach_counter_once_per_item():
    q = InMemoryHumanReview()
    obs = InMemoryObservability()
    q.enqueue(_item(sla_seconds=3600, enqueued_at=_T0))
    q.enqueue(_item(sla_seconds=3600, enqueued_at=_T0))
    monitor = SlaMonitor(q, obs)

    now = _T0 + timedelta(hours=2)
    first = monitor.sweep(now)
    assert len(first) == 2
    assert obs.counter(HUMAN_REVIEW_SLA_BREACH) == 2

    # A second sweep must not double-count the same breaches (idempotent).
    monitor.sweep(now)
    assert obs.counter(HUMAN_REVIEW_SLA_BREACH) == 2
    assert monitor.breach_count == 2


def test_resolved_items_are_not_overdue():
    q = InMemoryHumanReview()
    rid = q.enqueue(_item(sla_seconds=3600, enqueued_at=_T0))
    q.resolve(rid, "alice", "approved")
    assert q.overdue(_T0 + timedelta(hours=5)) == ()  # resolved → not counted as breached
