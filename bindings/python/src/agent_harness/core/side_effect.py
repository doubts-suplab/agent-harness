"""Side-effect gating policy (spec §5 T-5, §5.3, ADR-0011).

Every registered tool declares a side-effect class: ``none | read | write | external``. Before a tool
executes, the harness consults this policy. ``none``/``read`` calls are ungated (they observe, they do
not act). ``write``/``external`` calls are **gated**: they MUST clear a confidence threshold and MUST
NOT be issued by a read-only (``OBSERVE``-authority) agent. A gated call that fails the policy is
refused **before execution** and recorded as a security event — the side effect never happens.

This is the tool-call analogue of the confidence gate (§4): the gate decides ``auto_enforced`` for a
decision; this policy decides whether a side-effecting *tool call* may run. It is deliberately small;
the general ``PolicyPort`` (spec §7) is a later increment.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import AuthorityLevel

# The side-effect classes that are subject to gating (spec §5.3). ``none``/``read`` are ungated.
GATED_CLASSES = frozenset({"write", "external"})


@dataclass(frozen=True)
class SideEffectPolicy:
    """Confidence thresholds for gated side-effect classes. Never below the gate's base floor."""

    write_threshold: float = 0.85
    external_threshold: float = 0.95

    @staticmethod
    def is_gated(side_effect: str | None) -> bool:
        return side_effect in GATED_CLASSES

    def threshold_for(self, side_effect: str) -> float:
        if side_effect == "write":
            return self.write_threshold
        if side_effect == "external":
            return self.external_threshold
        return 0.0

    def permits(
        self,
        side_effect: str | None,
        confidence: float | None,
        authority: AuthorityLevel,
    ) -> bool:
        """True if a call with this side-effect class may execute (spec §5.3).

        Ungated classes always pass. For gated classes: a read-only (``OBSERVE``) agent is never
        permitted, and the supplied ``confidence`` (absent → 0.0) MUST meet the class threshold.
        """
        if not self.is_gated(side_effect):
            return True
        # OBSERVE agents are read-only — they never perform a write/external side effect.
        if authority <= AuthorityLevel.OBSERVE:
            return False
        c = confidence if confidence is not None else 0.0
        return c >= self.threshold_for(side_effect)  # type: ignore[arg-type]
