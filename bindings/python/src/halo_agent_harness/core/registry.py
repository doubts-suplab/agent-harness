"""The tool registry — the governance boundary for agent capabilities (spec §5, ADR-0004).

Default-deny: a tool not in an agent's allowlist is unreachable. No wildcards. Registration of a
wildcard allowlist is rejected. The registry also holds the concrete tool implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .errors import ToolNotAuthorizedError, ToolRegistrationError

ToolImpl = Callable[[dict[str, Any]], Any]

_SIDE_EFFECTS = frozenset({"none", "read", "write", "external"})


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    parameters: dict
    side_effect: str
    impl: ToolImpl


class ToolRegistry:
    """Holds tool implementations and per-agent allowlists; authorizes every call."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._allowlists: dict[str, frozenset[str]] = {}

    # -- registration ----------------------------------------------------
    def register_tool(
        self,
        name: str,
        impl: ToolImpl,
        *,
        description: str = "",
        parameters: dict | None = None,
        side_effect: str = "read",
    ) -> None:
        if "*" in name:
            raise ToolRegistrationError(f"tool name {name!r} must not contain a wildcard")
        if side_effect not in _SIDE_EFFECTS:
            raise ToolRegistrationError(f"unknown side_effect {side_effect!r}")
        self._tools[name] = RegisteredTool(
            name=name,
            description=description,
            parameters=parameters or {},
            side_effect=side_effect,
            impl=impl,
        )

    def grant(self, agent_name: str, tool_names: frozenset[str] | set[str] | list[str]) -> None:
        """Set an agent's explicit tool allowlist (spec §5 T-1, T-3). Wildcards are rejected."""
        names = frozenset(tool_names)
        for n in names:
            if "*" in n:
                raise ToolRegistrationError(f"wildcard permission {n!r} is forbidden (spec §5 T-3)")
        self._allowlists[agent_name] = names

    # -- authorization / invocation -------------------------------------
    def is_authorized(self, agent_name: str, tool_name: str) -> bool:
        return tool_name in self._allowlists.get(agent_name, frozenset())

    def allowlist(self, agent_name: str) -> frozenset[str]:
        return self._allowlists.get(agent_name, frozenset())

    def side_effect(self, tool_name: str) -> str | None:
        """The declared side-effect class of a tool (spec §5 T-5), or None if unregistered."""
        tool = self._tools.get(tool_name)
        return tool.side_effect if tool is not None else None

    def invoke(self, agent_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Authorize (default-deny) then invoke. Unauthorized → ToolNotAuthorizedError (spec §5 T-1/T-2)."""
        if not self.is_authorized(agent_name, tool_name):
            raise ToolNotAuthorizedError(agent_name, tool_name)
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolNotAuthorizedError(agent_name, tool_name)
        return tool.impl(arguments)
