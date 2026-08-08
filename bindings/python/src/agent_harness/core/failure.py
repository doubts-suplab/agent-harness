"""Failure-mode defaults (spec §8).

Every failure resolves to a *safe* decision: lowered confidence and ``auto_enforced=False``.
An agent never fails open into an autonomous action.
"""

from __future__ import annotations

import enum

from .model import Decision, DecisionAction


class FailureMode(enum.Enum):
    LLM_UNAVAILABLE = "llm_unavailable"
    MEMORY_TIMEOUT = "memory_timeout"
    MISSING_CONTEXT = "missing_context"
    TOOL_FAILURE = "tool_failure"
    BAD_OUTPUT = "bad_output"            # unexpected shape / confidence out of range
    OUT_OF_AUTHORITY = "out_of_authority"


# spec §8 default table. All fallbacks are non-enforcing (auto_enforced stays False).
_DEFAULTS: dict[FailureMode, tuple[DecisionAction, float]] = {
    FailureMode.LLM_UNAVAILABLE: (DecisionAction.ALLOW, 0.5),
    FailureMode.MEMORY_TIMEOUT: (DecisionAction.DEFER, 0.6),
    FailureMode.MISSING_CONTEXT: (DecisionAction.DEFER, 0.5),
    FailureMode.TOOL_FAILURE: (DecisionAction.DEFER, 0.6),
    FailureMode.BAD_OUTPUT: (DecisionAction.DEFER, 0.0),
    FailureMode.OUT_OF_AUTHORITY: (DecisionAction.DEFER, 0.0),
}


def default_for(mode: FailureMode, detail: str = "") -> Decision:
    """Return the safe fallback decision for a failure mode (spec §8)."""
    action, confidence = _DEFAULTS[mode]
    rationale = f"harness failure default ({mode.value})"
    if detail:
        rationale = f"{rationale}: {detail}"
    # auto_enforced is False and stays False — the gate will confirm it.
    return Decision(action=action, confidence=confidence, rationale=rationale, auto_enforced=False)
