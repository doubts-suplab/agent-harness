"""Orchestration patterns (spec §6). Supervisor+Workers is the primary multi-step pattern."""

from __future__ import annotations

from .supervisor import OrchestrationResult, SupervisorWorkers

__all__ = ["OrchestrationResult", "SupervisorWorkers"]
