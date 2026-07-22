# ADR-0006 — Decision envelope: reconciling the authority ladder with the decision-action enum

- **Status:** Accepted
- **Date:** 2026-07-22

## Context

AIEL defines two five-valued enumerations that have drifted apart across its documents:

- **Authority ladder** (`aether-iel/lifecycle/05-agent-engineering.md`):
  `OBSERVE < SUGGEST < ALERT < RATE_LIMIT < BLOCK`, each tied to a confidence threshold.
- **Decision/capability enum** (`aether-iel/templates/agent-contract.md`):
  `ALLOW | BLOCK | ALERT | SUGGEST | DEFER`.

They overlap (`SUGGEST`, `ALERT`, `BLOCK`) but are not the same set: the ladder has `OBSERVE`/`RATE_LIMIT`;
the enum has `ALLOW`/`DEFER`. Treating them as one enum is the source of the drift and would make the runtime
model ambiguous.

## Decision

Keep **both**, on **two separate axes**:

- **Authority Level** — the *static capability ceiling* of an agent (`OBSERVE…BLOCK`), declared once in the
  contract, immutable at runtime.
- **Decision Action** — the *dynamic outcome* of one invocation (`ALLOW…DEFER`), carried in
  `AgentOutput.decision.action`.

A **binding rule** (harness-protocol.md §3.3) maps each `DecisionAction` to the minimum Authority Level it
requires; the harness refuses out-of-authority actions. Cross-agent conflicts resolve via the Decision
Hierarchy `BLOCK > RATE_LIMIT > ALERT > SUGGEST > DEFER > ALLOW` (`governance-controls.md` §2.1).

## Rationale

- Separating "what an agent is *allowed* to do" from "what it *decided* this time" removes the ambiguity and
  matches how the runtime actually enforces authority (static gate) vs. records outcomes (dynamic).
- `DEFER` becomes a first-class, always-safe "send to a human" outcome distinct from the authority ladder.

## Consequences

- The contract schema carries both `authorityLevel` (single enum) and `capabilities` (list of DecisionActions).
- Validation ensures declared capabilities never exceed the authority level.
- Downstream consumers (apex `AgentResult`, grid `Agent` SPI) map onto the Decision axis; their authority
  configuration maps onto the Authority axis.
