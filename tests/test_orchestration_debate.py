"""Debate / Consensus tests (spec §6.4). Each participant still passes the gate (O-1); the consensus
never exceeds the strictest participant (safety floor)."""

from __future__ import annotations

import pytest

from agent_harness import (
    AuthorityLevel,
    BYPASS_COUNTER,
    ConsensusRule,
    Debate,
    DecisionAction,
    action_precedence,
    min_authority_for,
)
from conftest import FakeAgent, static_decision

_ALL = frozenset(
    {DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER}
)


def _agent(name, action, confidence, authority=AuthorityLevel.BLOCK):
    return FakeAgent(name, authority, _ALL, static_decision(action, confidence))


def test_debate_default_rule_is_safest(rig, request_):
    debate = Debate(rig.harness, [_agent("a", DecisionAction.ALLOW, 0.9)])
    assert debate._rule is ConsensusRule.SAFEST  # noqa: SLF001 — documenting the default


def test_debate_safest_rule_strictest_action_wins(rig, request_):
    participants = [
        _agent("a", DecisionAction.ALLOW, 0.9),
        _agent("b", DecisionAction.ALLOW, 0.9),
        _agent("c", DecisionAction.BLOCK, 0.97),
    ]
    result = Debate(rig.harness, participants, rule=ConsensusRule.SAFEST).run(request_)
    assert result.consensus_action is DecisionAction.BLOCK  # one BLOCK beats two ALLOWs
    assert result.tie is False


def test_debate_majority_rule_plurality_wins_and_may_deescalate(rig, request_):
    participants = [
        _agent("a", DecisionAction.ALLOW, 0.9),
        _agent("b", DecisionAction.ALLOW, 0.9),
        _agent("c", DecisionAction.BLOCK, 0.97),
    ]
    result = Debate(rig.harness, participants, rule=ConsensusRule.MAJORITY).run(request_)
    assert result.consensus_action is DecisionAction.ALLOW  # majority de-escalates (2 ALLOW > 1 BLOCK)
    assert result.tie is False


def test_debate_majority_tie_resolves_to_defer(rig, request_):
    participants = [
        _agent("a", DecisionAction.ALLOW, 0.9),
        _agent("b", DecisionAction.BLOCK, 0.97),
    ]
    result = Debate(rig.harness, participants, rule=ConsensusRule.MAJORITY).run(request_)
    assert result.consensus_action is DecisionAction.DEFER  # tie -> human review
    assert result.tie is True


@pytest.mark.parametrize("rule", [ConsensusRule.SAFEST, ConsensusRule.MAJORITY])
def test_debate_consensus_never_exceeds_strictest_participant(rig, request_, rule):
    # Mixed authorities; the strictest proposed action is ALERT. Consensus must not exceed it.
    participants = [
        _agent("a", DecisionAction.ALLOW, 0.9, authority=AuthorityLevel.OBSERVE),
        _agent("b", DecisionAction.ALERT, 0.9, authority=AuthorityLevel.ALERT),
        _agent("c", DecisionAction.ALLOW, 0.9, authority=AuthorityLevel.OBSERVE),
    ]
    result = Debate(rig.harness, participants, rule=rule).run(request_)
    proposed = [o.decision.action for o in result.participant_outputs.values()]
    strictest = max(proposed, key=action_precedence)
    # Consensus never exceeds the strictest proposed action's severity...
    assert action_precedence(result.consensus_action) <= action_precedence(strictest)
    # ...and never requires more authority than the strictest participant holds.
    assert min_authority_for(result.consensus_action) <= min_authority_for(strictest)


def test_debate_each_participant_passes_the_gate_bypass_zero(rig, request_):
    participants = [_agent("a", DecisionAction.BLOCK, 0.97), _agent("b", DecisionAction.ALERT, 0.9)]
    Debate(rig.harness, participants).run(request_)
    assert rig.obs.counter(BYPASS_COUNTER) == 0
    assert len(rig.audit.entries) == 2  # O-1: each participant went through the harness


def test_debate_requires_at_least_one_participant(rig):
    with pytest.raises(ValueError):
        Debate(rig.harness, [])
