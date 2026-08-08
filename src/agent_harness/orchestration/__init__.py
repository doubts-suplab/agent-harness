"""Orchestration patterns (spec §6). Supervisor+Workers is the primary multi-step pattern."""

from __future__ import annotations

from .debate import Debate, DebateResult, ConsensusRule
from .fanout import FanOut, FanOutResult
from .pipeline import Pipeline, PipelineResult
from .supervisor import OrchestrationResult, SupervisorWorkers

__all__ = [
    "OrchestrationResult",
    "SupervisorWorkers",
    "Pipeline",
    "PipelineResult",
    "FanOut",
    "FanOutResult",
    "Debate",
    "DebateResult",
    "ConsensusRule",
]
