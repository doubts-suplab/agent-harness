"""Parallel Fan-out tests (spec §6.2). Workers run concurrently; each still passes the gate (O-1)."""

from __future__ import annotations

import threading

import pytest

from agent_harness import (
    AuthorityLevel,
    BYPASS_COUNTER,
    Decision,
    DecisionAction,
    FanOut,
)
from conftest import FakeAgent, static_decision


def _agent(name, action, confidence, decide=None):
    return FakeAgent(
        name,
        AuthorityLevel.BLOCK,
        frozenset({DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER}),
        decide or static_decision(action, confidence),
    )


def test_fanout_runs_all_workers_and_reconciles_to_safest(rig, request_):
    workers = [
        _agent("w1", DecisionAction.ALLOW, 0.9),
        _agent("w2", DecisionAction.ALERT, 0.9),
        _agent("w3", DecisionAction.BLOCK, 0.97),
    ]
    result = FanOut(rig.harness, workers).run(request_)
    assert result.reconciled_action is DecisionAction.BLOCK  # BLOCK wins the hierarchy
    assert set(result.worker_outputs) == {"w1", "w2", "w3"}


def test_fanout_worker_outputs_are_order_stable(rig, request_):
    workers = [_agent(f"w{i}", DecisionAction.ALLOW, 0.9) for i in range(5)]
    result = FanOut(rig.harness, workers).run(request_)
    assert list(result.worker_outputs) == ["w0", "w1", "w2", "w3", "w4"]


def test_fanout_each_worker_passes_the_gate_bypass_zero(rig, request_):
    workers = [_agent("w1", DecisionAction.BLOCK, 0.97), _agent("w2", DecisionAction.ALERT, 0.9)]
    FanOut(rig.harness, workers).run(request_)
    assert rig.obs.counter(BYPASS_COUNTER) == 0
    assert len(rig.audit.entries) == 2  # O-1: each worker went through the harness


def test_fanout_actually_runs_workers_concurrently(rig, request_):
    # A barrier of N only releases if all N workers reach it at once. If fan-out ran sequentially,
    # the first worker's wait would time out (BrokenBarrierError), the harness would return a safe
    # DEFER, and the reconciliation would not be the intended ALERT.
    n = 4
    barrier = threading.Barrier(n, timeout=3)

    def waiting(_req, _tools):
        barrier.wait()
        return Decision(DecisionAction.ALERT, 0.9, "reached the barrier")

    workers = [_agent(f"w{i}", None, 0, waiting) for i in range(n)]
    result = FanOut(rig.harness, workers).run(request_)

    assert result.reconciled_action is DecisionAction.ALERT
    assert all(o.decision.action is DecisionAction.ALERT for o in result.worker_outputs.values())


def test_fanout_any_auto_enforced(rig, request_):
    workers = [_agent("w1", DecisionAction.ALLOW, 0.5), _agent("w2", DecisionAction.BLOCK, 0.97)]
    result = FanOut(rig.harness, workers).run(request_)
    assert result.any_auto_enforced is True


def test_fanout_requires_at_least_one_worker(rig):
    with pytest.raises(ValueError):
        FanOut(rig.harness, [])
