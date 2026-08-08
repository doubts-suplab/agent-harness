"""Cross-process kill-switch (file signal) tests (spec §7.6)."""

from __future__ import annotations

from agent_harness import AgentInput, AuthorityLevel, DecisionAction, Harness
from agent_harness.adapters import FileKillSwitch
from conftest import FakeAgent, static_decision


def test_starts_disengaged(tmp_path):
    assert FileKillSwitch(tmp_path / "kill").is_engaged() is False


def test_engage_and_disengage_are_idempotent(tmp_path):
    ks = FileKillSwitch(tmp_path / "nested" / "kill")
    ks.engage()
    ks.engage()  # idempotent
    assert ks.is_engaged() is True
    ks.disengage()
    ks.disengage()  # idempotent
    assert ks.is_engaged() is False


def test_trip_propagates_across_instances(tmp_path):
    # Two adapters over the same path stand in for two processes.
    path = tmp_path / "kill"
    proc_a = FileKillSwitch(path)
    proc_b = FileKillSwitch(path)
    proc_a.engage()
    assert proc_b.is_engaged() is True  # the other "process" sees the trip
    proc_b.disengage()
    assert proc_a.is_engaged() is False


def test_engaged_switch_routes_everything_to_human_review(tmp_path):
    path = tmp_path / "kill"
    kill = FileKillSwitch(path)
    kill.engage()
    harness = Harness(kill_switch=kill)
    agent = FakeAgent("a", AuthorityLevel.BLOCK, frozenset({DecisionAction.BLOCK}),
                      static_decision(DecisionAction.BLOCK, 0.99))
    out = harness.invoke(agent, AgentInput("t1", "u1"))
    assert out.decision.action is DecisionAction.DEFER   # short-circuited by the kill switch
    assert out.decision.auto_enforced is False
