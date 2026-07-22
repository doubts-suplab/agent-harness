"""Agent protocol and the tool-invocation boundary (spec §2, §5, §10).

An agent proposes a Decision; it never sets ``auto_enforced`` and it can only reach tools through the
``ToolInvoker`` the harness hands it (which enforces the registry allowlist).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .model import AgentInput, AuthorityLevel, Decision, DecisionAction


@runtime_checkable
class ToolInvoker(Protocol):
    """Scoped tool access handed to an agent for one invocation.

    ``call`` authorizes against the agent's registry allowlist *before* any side effect (spec §5);
    an unauthorized name raises ``ToolNotAuthorizedError`` and is recorded as a security event.
    """

    def call(self, tool_name: str, arguments: dict[str, Any]) -> Any: ...


@runtime_checkable
class Agent(Protocol):
    """A decision-making agent (spec §10).

    Attributes mirror the Agent Contract: a stable name, a static authority ceiling, and the set of
    DecisionActions it may emit. The harness enforces the gate, registry, and authority around ``run``.
    """

    name: str
    authority_level: AuthorityLevel
    capabilities: frozenset[DecisionAction]

    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        """Produce a Decision. MUST NOT set ``auto_enforced`` (the harness owns it)."""
        ...
