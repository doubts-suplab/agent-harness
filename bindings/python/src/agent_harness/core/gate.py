"""The confidence gate (spec §4, ADR-0003).

Centralized, runs on every invocation, and cannot be disabled. It is the *only* place ``auto_enforced``
is set. Agents cannot reach it.
"""

from __future__ import annotations

from .model import AuthorityLevel, Decision, DecisionAction

# spec §3.1 / §4: auto-enforce thresholds per authority level.
_THRESHOLDS: dict[AuthorityLevel, float] = {
    AuthorityLevel.ALERT: 0.80,
    AuthorityLevel.RATE_LIMIT: 0.85,
    AuthorityLevel.BLOCK: 0.95,
}

# G-3: the floor for any externally-effecting action. The gate never enforces below this.
BASE_THRESHOLD = 0.80

# Actions that never take autonomous effect — always routed to a human (spec §3.3).
_ALWAYS_REVIEW_ACTIONS = frozenset({DecisionAction.DEFER, DecisionAction.SUGGEST})


class ConfidenceGate:
    """Decides ``auto_enforced`` for a decision. There is no 'disabled' state (G-4).

    The gate never trusts an incoming ``auto_enforced`` flag — it always recomputes it.
    """

    def threshold_for(self, authority: AuthorityLevel) -> float:
        """Effective auto-enforce threshold for an authority level (never below BASE_THRESHOLD)."""
        return max(BASE_THRESHOLD, _THRESHOLDS.get(authority, BASE_THRESHOLD))

    def evaluate(self, decision: Decision, authority: AuthorityLevel) -> bool:
        """Compute whether ``decision`` may auto-enforce, and stamp it onto the decision.

        Returns the resulting ``auto_enforced`` value (also written to ``decision.auto_enforced``).
        """
        auto = self._compute(decision, authority)
        decision.auto_enforced = auto
        return auto

    def _compute(self, decision: Decision, authority: AuthorityLevel) -> bool:
        # G-5: OBSERVE/SUGGEST-authority agents never auto-enforce, regardless of confidence.
        if authority <= AuthorityLevel.SUGGEST:
            return False
        # DEFER/SUGGEST outcomes always route to a human (spec §3.3).
        if decision.action in _ALWAYS_REVIEW_ACTIONS:
            return False
        # ALLOW has no external effect; it is "enforced" trivially only when confidence clears the bar.
        return decision.confidence >= self.threshold_for(authority)

    def is_bypass(self, decision: Decision, authority: AuthorityLevel) -> bool:
        """A bypass is an auto-enforced decision that should not have cleared the gate.

        In a correct system this is always False (spec §4.2: ``confidence_gate_bypass_total`` == 0).
        Used defensively by the harness to feed the bypass counter.
        """
        if not decision.auto_enforced:
            return False
        return self._compute(decision, authority) is False
