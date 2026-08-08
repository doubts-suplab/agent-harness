"""Pipeline orchestration tests (spec §6.1). Every stage still passes the gate + registry (O-1)."""

from __future__ import annotations

import pytest

from agent_harness import (
    AuthorityLevel,
    BYPASS_COUNTER,
    Decision,
    DecisionAction,
    Pipeline,
)
from conftest import FakeAgent, static_decision


def _agent(name, action, confidence, decide=None):
    return FakeAgent(
        name,
        AuthorityLevel.BLOCK,
        frozenset({DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER}),
        decide or static_decision(action, confidence),
    )


def test_pipeline_runs_all_stages_in_order(rig, request_):
    order: list[str] = []

    def track(name):
        def _decide(_req, _tools):
            order.append(name)
            return Decision(DecisionAction.ALLOW, 0.9, "ok")

        return _decide

    stages = [_agent("s1", None, 0, track("s1")), _agent("s2", None, 0, track("s2")),
              _agent("s3", None, 0, track("s3"))]
    result = Pipeline(rig.harness, stages).run(request_)

    assert order == ["s1", "s2", "s3"]
    assert list(result.stage_outputs) == ["s1", "s2", "s3"]
    assert result.final_action is DecisionAction.ALLOW
    assert result.short_circuited_at is None


def test_pipeline_passes_prior_decision_into_next_stage_context(rig, request_):
    seen: dict = {}

    def s1_decide(_req, _tools):
        return Decision(DecisionAction.ALERT, 0.9, "raise an alert")

    def s2_decide(req, _tools):
        seen.update(req.context.get("pipeline", {}))
        return Decision(DecisionAction.ALLOW, 0.9, "ok")

    stages = [_agent("s1", None, 0, s1_decide), _agent("s2", None, 0, s2_decide)]
    Pipeline(rig.harness, stages).run(request_)

    assert seen["prior_stage"] == "s1"
    assert seen["prior_action"] == "ALERT"
    assert seen["prior_confidence"] == 0.9
    assert seen["prior_rationale"] == "raise an alert"


@pytest.mark.parametrize("stop_action", [DecisionAction.BLOCK, DecisionAction.DEFER])
def test_pipeline_short_circuits_on_block_or_defer(rig, request_, stop_action):
    ran: list[str] = []

    def make(name, action):
        def _decide(_req, _tools):
            ran.append(name)
            return Decision(action, 0.9, "stop" if action in (DecisionAction.BLOCK, DecisionAction.DEFER) else "ok")

        return _decide

    stages = [
        _agent("s1", None, 0, make("s1", DecisionAction.ALLOW)),
        _agent("s2", None, 0, make("s2", stop_action)),
        _agent("s3", None, 0, make("s3", DecisionAction.ALLOW)),
    ]
    result = Pipeline(rig.harness, stages).run(request_)

    assert ran == ["s1", "s2"]  # s3 never runs
    assert result.short_circuited_at == "s2"
    assert result.final_action is stop_action


def test_pipeline_each_stage_passes_the_gate_bypass_zero(rig, request_):
    stages = [_agent("s1", DecisionAction.ALERT, 0.96), _agent("s2", DecisionAction.ALLOW, 0.9)]
    Pipeline(rig.harness, stages).run(request_)
    assert rig.obs.counter(BYPASS_COUNTER) == 0
    # Two invocations → two audit entries (O-1: each stage went through the harness).
    assert len(rig.audit.entries) == 2


def test_pipeline_reconciled_action_is_the_safest_seen(rig, request_):
    stages = [_agent("s1", DecisionAction.ALLOW, 0.9), _agent("s2", DecisionAction.ALERT, 0.9)]
    result = Pipeline(rig.harness, stages).run(request_)
    assert result.reconciled_action is DecisionAction.ALERT


def test_pipeline_requires_at_least_one_stage(rig):
    with pytest.raises(ValueError):
        Pipeline(rig.harness, [])
