"""Pluggable PII/secret redaction (spec §7.3).

Redaction runs before every audit write; zero PII in logs is a P1 condition. The default strategy
covers common patterns (JWT, email, card, SSN, phone, API key) — but every deployment has its own
sensitive shapes, so the strategy is **pluggable**: extend it with ``with_rule`` or build one from
scratch. A ``RedactionStrategy`` is callable, so it drops directly into any port that takes a
``redactor``.

The default patterns are best-effort, not a guarantee: order matters (specific before generic) and no
regex set is exhaustive. Treat redaction as defense-in-depth, not the only control.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class RedactionRule:
    pattern: re.Pattern[str]
    replacement: str


# spec §7.3 default rules. Order matters (JWT/card before generic digit runs).
_DEFAULT_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[REDACTED_JWT]"),
    RedactionRule(re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    RedactionRule(re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CARD]"),
    RedactionRule(re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    RedactionRule(re.compile(r"\b(?:\+?\d[\d -]{8,}\d)\b"), "[REDACTED_PHONE]"),
    RedactionRule(re.compile(r"\b(?:sk|pk|ghp|xox[baprs])[-_][A-Za-z0-9]{8,}\b"), "[REDACTED_KEY]"),
)


@dataclass(frozen=True)
class RedactionStrategy:
    """An ordered, immutable set of redaction rules. Callable so it plugs in wherever a redactor is asked."""

    rules: tuple[RedactionRule, ...] = field(default=_DEFAULT_RULES)

    def redact(self, text: str) -> str:
        out = text
        for rule in self.rules:
            out = rule.pattern.sub(rule.replacement, out)
        return out

    def __call__(self, text: str) -> str:
        return self.redact(text)

    def with_rule(self, pattern: str | re.Pattern[str], replacement: str) -> "RedactionStrategy":
        """Return a new strategy with one extra rule appended (the base stays immutable)."""
        compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
        return replace(self, rules=self.rules + (RedactionRule(compiled, replacement),))


DEFAULT_STRATEGY = RedactionStrategy()


def redact(text: str) -> str:
    """Redact with the default strategy (spec §7.3). Kept as a free function for convenience."""
    return DEFAULT_STRATEGY.redact(text)
