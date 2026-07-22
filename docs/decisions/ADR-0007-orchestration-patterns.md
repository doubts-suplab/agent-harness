# ADR-0007 — Orchestration pattern set; the supervisor-holds-no-tools invariant

- **Status:** Accepted
- **Date:** 2026-07-22

## Context

AIEL Phase 5 enumerates four agent-interaction patterns (Sequential Pipeline, Parallel Fan-out,
Supervisor + Workers, Debate/Consensus) and states that Supervisor + Workers is "the primary pattern for
complex, multi-step tasks," with the constraint that "the supervisor holds no tool permissions — it only
coordinates."

## Decision

The harness provides exactly these four composable orchestration patterns. **Supervisor + Workers** is the
recommended default for multi-step tasks. A supervisor agent **MUST** hold an **empty** tool allowlist
(enforced by the tool registry, ADR-0004). Every agent invocation inside any orchestration passes through the
confidence gate (ADR-0003) and tool registry (ADR-0004) **individually** — orchestration composes agents; it
never bypasses their controls.

## Rationale

- A small, fixed pattern set keeps orchestration reasoning tractable and auditable.
- The no-tools supervisor rule prevents a coordinator from accumulating de-facto authority over side effects.
- Per-invocation control application means composition can never be used to launder an ungated action.

## Consequences

- Orchestrations are themselves framework-free sequencers that reconcile `Decision`s via the Decision
  Hierarchy (ADR-0006).
- Reference implementation (Increment 1) will implement Supervisor + Workers first as the primary pattern.
