"""PolicyPort reference adapter (spec §7) — evaluate action against immutable rules.

Rules are fixed at construction (frozen dataclasses): a policy cannot be mutated at runtime, which
upholds the no-self-escalation invariant (INV-3) — an agent cannot loosen the rules that bind it. The
first matching rule wins; if none match, the configured default applies. ``load_policy`` builds the same
immutable policy from a durable JSON file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PolicyRule:
    """A single allow/deny rule. ``None`` in a field means 'any' (not a wildcard string — an explicit any)."""

    effect: str                     # "allow" | "deny"
    agent: str | None = None
    action: str | None = None
    tenant: str | None = None

    def __post_init__(self) -> None:
        if self.effect not in ("allow", "deny"):
            raise ValueError(f"rule effect must be 'allow' or 'deny', got {self.effect!r}")

    def matches(self, agent_name: str, action: str, tenant_id: str) -> bool:
        return (
            (self.agent is None or self.agent == agent_name)
            and (self.action is None or self.action == action)
            and (self.tenant is None or self.tenant == tenant_id)
        )


@dataclass(frozen=True)
class RuleBasedPolicy:
    """Immutable rule set. First matching rule wins; otherwise ``default_allow`` decides."""

    rules: tuple[PolicyRule, ...] = field(default_factory=tuple)
    default_allow: bool = True

    def permits(self, agent_name: str, action: str, tenant_id: str) -> bool:
        for rule in self.rules:
            if rule.matches(agent_name, action, tenant_id):
                return rule.effect == "allow"
        return self.default_allow


def load_policy(path: str | Path) -> RuleBasedPolicy:
    """Load an immutable policy from a JSON file: ``{"default_allow": bool, "rules": [ {...}, ... ]}``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules = tuple(
        PolicyRule(
            effect=r["effect"],
            agent=r.get("agent"),
            action=r.get("action"),
            tenant=r.get("tenant"),
        )
        for r in data.get("rules", [])
    )
    return RuleBasedPolicy(rules=rules, default_allow=bool(data.get("default_allow", True)))
