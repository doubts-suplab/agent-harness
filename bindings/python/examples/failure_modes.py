"""Failure modes — the harness never fails open (spec §8).

Run:  python examples/failure_modes.py

Every failure resolves to a *safe*, non-enforcing decision. This shows four paths: an agent that
raises, an unauthorized tool call, a low-confidence decision, and an engaged kill switch — each ends up
at a safe default routed to human review, with the gate never bypassed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from halo_agent_harness import AgentInput, AuthorityLevel, Decision, DecisionAction, Harness
from halo_agent_harness.adapters import InMemoryAudit, InMemoryHumanReview, InMemoryKillSwitch, InMemoryObservability
from halo_agent_harness.core.agent import ToolInvoker

_ALL = frozenset({DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER})


@dataclass
class ScriptedAgent:
    name: str
    behaviour: str  # "raise" | "bad-tool" | "low-confidence" | "ok"
    authority_level: AuthorityLevel = AuthorityLevel.BLOCK
    capabilities: frozenset = field(default_factory=lambda: _ALL)

    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        if self.behaviour == "raise":
            raise RuntimeError("LLM exploded")
        if self.behaviour == "bad-tool":
            tools.call("unregistered-tool", {})  # not on the allowlist -> refused before any effect
        if self.behaviour == "low-confidence":
            return Decision(DecisionAction.BLOCK, 0.4, "unsure, but wants to block")
        return Decision(DecisionAction.ALLOW, 0.99, "all good")


def _run(label: str, behaviour: str, *, kill: bool = False) -> None:
    audit, review, obs = InMemoryAudit(), InMemoryHumanReview(), InMemoryObservability()
    ks = InMemoryKillSwitch(engaged=kill)
    harness = Harness(audit=audit, human_review=review, observability=obs, kill_switch=ks)
    out = harness.invoke(ScriptedAgent("demo", behaviour), AgentInput("acme", "u1"))
    sec = [e.kind for e in audit.security_events]
    print(f"{label:16} -> action={out.decision.action.value:6} "
          f"auto_enforced={out.decision.auto_enforced!s:5} "
          f"review_queued={len(review.items)} security_events={sec}")


def main() -> None:
    _run("agent raises", "raise")
    _run("unauthorized tool", "bad-tool")
    _run("low confidence", "low-confidence")
    _run("kill switch", "ok", kill=True)
    print("\nEvery path resolved to a safe, non-enforcing decision — the harness never failed open.")


if __name__ == "__main__":
    main()
