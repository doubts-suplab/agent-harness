"""agent-harness — generic, enterprise-grade agent runtime (reference implementation).

Conforms to docs/spec/harness-protocol.md. The core (``core``, ``ports``, ``orchestration``) is
framework-free; adapters live under ``adapters``.
"""

from __future__ import annotations

from .core.agent import Agent, ToolInvoker
from .core.errors import (
    AuthorityViolationError,
    ContractValidationError,
    HarnessError,
    ToolNotAuthorizedError,
    ToolRegistrationError,
    UnscopedInvocationError,
)
from .core.failure import FailureMode, default_for
from .core.gate import BASE_THRESHOLD, ConfidenceGate
from .core.harness import BYPASS_COUNTER, Harness
from .core.model import (
    AgentInput,
    AgentOutput,
    AuthorityLevel,
    Decision,
    DecisionAction,
    action_within_authority,
    min_authority_for,
    reconcile,
)
from .core.registry import ToolRegistry
from .orchestration.pipeline import Pipeline, PipelineResult
from .orchestration.supervisor import OrchestrationResult, SupervisorWorkers

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "ToolInvoker",
    "AgentInput",
    "AgentOutput",
    "Decision",
    "DecisionAction",
    "AuthorityLevel",
    "action_within_authority",
    "min_authority_for",
    "reconcile",
    "ConfidenceGate",
    "BASE_THRESHOLD",
    "ToolRegistry",
    "Harness",
    "BYPASS_COUNTER",
    "SupervisorWorkers",
    "OrchestrationResult",
    "Pipeline",
    "PipelineResult",
    "FailureMode",
    "default_for",
    "HarnessError",
    "UnscopedInvocationError",
    "ToolNotAuthorizedError",
    "ToolRegistrationError",
    "AuthorityViolationError",
    "ContractValidationError",
    "__version__",
]
