"""Debate / Consensus orchestration (spec §6.4).

Multiple agents produce competing decisions over the same ``AgentInput``; a **consensus rule**
reconciles them. Every participant is invoked through ``Harness.invoke``, so each passes the confidence
gate and tool registry individually (O-1).

Two consensus rules are provided:

- ``SAFEST`` (default) — the strictest action wins, per the Decision Hierarchy (§3.3). Conservative:
  a single ``BLOCK`` beats any number of ``ALLOW``s. This is the safe default for governance.
- ``MAJORITY`` — the most-proposed action wins; a tie resolves to ``DEFER`` (tie → human review).
  ``MAJORITY`` may *de-escalate* below the strictest proposal (that is the point of a vote); use
  ``SAFEST`` when the strictest participant must always win.

**Safety floor (invariant).** Consensus can never *raise* authority above the strictest participant:
the consensus action's severity never exceeds the strictest action any participant actually proposed.
Since every rule chooses among proposed actions, this holds by construction; it is enforced defensively
and asserted by tests.
"""

from __future__ import annotations

import enum
from collections import Counter
from dataclasses import dataclass

from ..core.agent import Agent
from ..core.harness import Harness
from ..core.model import (
    AgentInput,
    AgentOutput,
    DecisionAction,
    action_precedence,
    reconcile,
)


class ConsensusRule(enum.Enum):
    SAFEST = "safest"      # strictest action wins (Decision Hierarchy §3.3)
    MAJORITY = "majority"  # plurality; tie -> DEFER (routes to human review)


@dataclass(frozen=True)
class DebateResult:
    """The reconciled outcome of a debate."""

    consensus_action: DecisionAction
    rule: ConsensusRule
    participant_outputs: dict[str, AgentOutput]
    tie: bool = False

    @property
    def any_auto_enforced(self) -> bool:
        return any(o.decision.auto_enforced for o in self.participant_outputs.values())


class Debate:
    """Runs competing agents and reconciles their decisions with a consensus rule."""

    def __init__(
        self,
        harness: Harness,
        participants: list[Agent],
        *,
        rule: ConsensusRule = ConsensusRule.SAFEST,
    ) -> None:
        if not participants:
            raise ValueError("a debate requires at least one participant")
        self._harness = harness
        self._participants = list(participants)
        self._rule = rule

    def run(self, request: AgentInput) -> DebateResult:
        outputs = {p.name: self._harness.invoke(p, request) for p in self._participants}
        actions = [o.decision.action for o in outputs.values()]

        action, tie = self._consensus(actions)

        # Safety floor (§6.4): never exceed the strictest action any participant proposed.
        ceiling = reconcile(actions)
        if action_precedence(action) > action_precedence(ceiling):
            action = ceiling

        return DebateResult(
            consensus_action=action,
            rule=self._rule,
            participant_outputs=outputs,
            tie=tie,
        )

    def _consensus(self, actions: list[DecisionAction]) -> tuple[DecisionAction, bool]:
        if self._rule is ConsensusRule.SAFEST:
            return reconcile(actions), False

        # MAJORITY: highest vote count wins; a tie for the top count resolves to DEFER.
        counts = Counter(actions)
        top = max(counts.values())
        winners = [a for a, c in counts.items() if c == top]
        if len(winners) == 1:
            return winners[0], False
        return DecisionAction.DEFER, True
