"""Supervisor + Workers planning-turn tests (spec §6.3). The supervisor is invoked through the harness
(governed, tool-less); it can halt delegation and, if it is a Planner, select which workers run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from agent_harness import (
    AgentInput,
    AuthorityLevel,
    BYPASS_COUNTER,
    Decision,
    DecisionAction,
    SupervisorWorkers,
)
from agent_harness.core.agent import ToolInvoker
from conftest import FakeAgent, static_decision

_ALL = frozenset(
    {DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER}
)


def _sup(action, confidence):
    # Supervisor holds no tools; authority high enough to emit any coordinating action.
    return FakeAgent("sup", AuthorityLevel.BLOCK, _ALL, static_decision(action, confidence))


def _worker(name, action, confidence, authority=AuthorityLevel.BLOCK):
    return FakeAgent(name, authority, _ALL, static_decision(action, confidence))


@dataclass
class PlanningSupervisor:
    """A supervisor that is also a Planner — selects a subset of workers."""

    name: str
    authority_level: AuthorityLevel
    capabilities: frozenset
    decide: Callable
    selector: Callable[[AgentInput, list[str]], list[str]]

    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        return self.decide(request, tools)

    def plan(self, request: AgentInput, worker_names: list[str]) -> list[str]:
        return self.selector(request, worker_names)


def test_supervisor_planning_turn_is_governed(rig, request_):
    sup = _sup(DecisionAction.ALLOW, 0.9)
    workers = [_worker("w1", DecisionAction.ALLOW, 0.9), _worker("w2", DecisionAction.ALERT, 0.9)]
    result = SupervisorWorkers(rig.harness, sup, workers).run(request_)
    # Supervisor + both workers each went through the harness → 3 audit entries (O-1).
    assert len(rig.audit.entries) == 3
    assert result.supervisor_output is not None
    assert result.supervisor_output.agent_name == "sup"
    assert rig.obs.counter(BYPASS_COUNTER) == 0


@pytest.mark.parametrize("halt_action", [DecisionAction.BLOCK, DecisionAction.DEFER])
def test_supervisor_halts_delegation(rig, request_, halt_action):
    sup = _sup(halt_action, 0.97)
    ran: list[str] = []

    def tracking(name):
        def _decide(_req, _tools):
            ran.append(name)
            return Decision(DecisionAction.ALLOW, 0.9, "ok")

        return _decide

    workers = [FakeAgent("w1", AuthorityLevel.BLOCK, _ALL, tracking("w1"))]
    result = SupervisorWorkers(rig.harness, sup, workers).run(request_)

    assert result.halted is True
    assert ran == []  # no worker ran
    assert result.worker_outputs == {}
    assert result.reconciled_action is halt_action


def test_supervisor_planner_selects_subset(rig, request_):
    sup = PlanningSupervisor(
        "sup", AuthorityLevel.BLOCK, _ALL,
        static_decision(DecisionAction.ALLOW, 0.9),
        selector=lambda _req, names: ["w2"],
    )
    workers = [
        _worker("w1", DecisionAction.BLOCK, 0.97),
        _worker("w2", DecisionAction.ALERT, 0.9),
    ]
    result = SupervisorWorkers(rig.harness, sup, workers).run(request_)

    assert result.delegated == ("w2",)
    assert set(result.worker_outputs) == {"w2"}
    assert result.reconciled_action is DecisionAction.ALERT  # w1 (BLOCK) was never engaged


def test_supervisor_plan_is_constrained_to_the_roster(rig, request_):
    sup = PlanningSupervisor(
        "sup", AuthorityLevel.BLOCK, _ALL,
        static_decision(DecisionAction.ALLOW, 0.9),
        selector=lambda _req, names: ["w1", "ghost"],  # "ghost" is not a worker
    )
    workers = [_worker("w1", DecisionAction.ALLOW, 0.9)]
    result = SupervisorWorkers(rig.harness, sup, workers).run(request_)
    assert result.delegated == ("w1",)  # bogus name filtered out


def test_supervisor_delegates_to_all_by_default(rig, request_):
    sup = _sup(DecisionAction.ALLOW, 0.9)
    workers = [_worker("w1", DecisionAction.ALLOW, 0.9), _worker("w2", DecisionAction.BLOCK, 0.97)]
    result = SupervisorWorkers(rig.harness, sup, workers).run(request_)
    assert set(result.delegated) == {"w1", "w2"}
    assert result.reconciled_action is DecisionAction.BLOCK
