"""Harness error taxonomy."""

from __future__ import annotations


class HarnessError(Exception):
    """Base class for all harness errors."""


class UnscopedInvocationError(HarnessError):
    """AgentInput is missing tenant/user scope (spec §2.1)."""


class ToolNotAuthorizedError(HarnessError):
    """An agent attempted a tool not in its allowlist (spec §5, INV-2).

    Raised before any side effect; recorded as a security event by the harness.
    """

    def __init__(self, agent_name: str, tool_name: str) -> None:
        super().__init__(f"agent {agent_name!r} is not authorized to call tool {tool_name!r}")
        self.agent_name = agent_name
        self.tool_name = tool_name


class ToolRegistrationError(HarnessError):
    """Invalid tool-registry configuration (e.g. a wildcard allowlist, spec §5 T-3)."""


class AuthorityViolationError(HarnessError):
    """An agent emitted an action beyond its authority level (spec §3.3)."""


class ContractValidationError(HarnessError):
    """An Agent Contract failed schema validation (spec §10)."""
