"""Sequential Pipeline orchestration (spec §6.1).

Agents run in order. Each stage receives the prior stage's decision in its ``context`` under the
``pipeline`` key, so a later stage can react to what came before. Every stage is invoked through
``Harness.invoke``, so each passes the confidence gate and tool registry individually (O-1).

The pipeline short-circuits on the first ``BLOCK`` or ``DEFER`` (spec §6.1): once a stage refuses or
defers, later stages do not run — the safe action stands and no further side effects are risked.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.agent import Agent
from ..core.harness import Harness
from ..core.model import AgentInput, AgentOutput, DecisionAction, reconcile

# Actions that stop the pipeline (spec §6.1) — the safer outcomes that must not be overridden by a
# later, more permissive stage.
_SHORT_CIRCUIT = frozenset({DecisionAction.BLOCK, DecisionAction.DEFER})


@dataclass(frozen=True)
class PipelineResult:
    """The outcome of a sequential pipeline run."""

    final_action: DecisionAction
    stage_outputs: dict[str, AgentOutput]
    short_circuited_at: str | None = None

    @property
    def reconciled_action(self) -> DecisionAction:
        """The safest action across every stage that actually ran (spec §3.3)."""
        return reconcile([o.decision.action for o in self.stage_outputs.values()])

    @property
    def any_auto_enforced(self) -> bool:
        return any(o.decision.auto_enforced for o in self.stage_outputs.values())


class Pipeline:
    """Runs agents sequentially, feeding each stage the prior stage's decision."""

    def __init__(self, harness: Harness, stages: list[Agent]) -> None:
        if not stages:
            raise ValueError("a pipeline requires at least one stage")
        self._harness = harness
        self._stages = list(stages)

    def run(self, request: AgentInput) -> PipelineResult:
        outputs: dict[str, AgentOutput] = {}
        short_circuited_at: str | None = None
        current = request

        for stage in self._stages:
            output = self._harness.invoke(stage, current)
            outputs[stage.name] = output
            action = output.decision.action
            if action in _SHORT_CIRCUIT:
                short_circuited_at = stage.name
                break
            current = _with_prior(request, stage.name, output)

        final_action = outputs[list(outputs)[-1]].decision.action
        return PipelineResult(
            final_action=final_action,
            stage_outputs=outputs,
            short_circuited_at=short_circuited_at,
        )


def _with_prior(base: AgentInput, stage_name: str, output: AgentOutput) -> AgentInput:
    """Return a new AgentInput carrying the prior stage's decision in ``context['pipeline']``.

    ``AgentInput`` is frozen; scope and metadata are preserved verbatim (spec §2.1).
    """
    decision = output.decision
    context = dict(base.context)
    context["pipeline"] = {
        "prior_stage": stage_name,
        "prior_action": decision.action.value,
        "prior_confidence": decision.confidence,
        "prior_rationale": decision.rationale,
    }
    return AgentInput(
        tenant_id=base.tenant_id,
        user_id=base.user_id,
        context=context,
        metadata=base.metadata,
    )
