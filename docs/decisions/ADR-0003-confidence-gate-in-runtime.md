# ADR-0003 — The confidence gate lives in the runtime, centralized and non-disableable

- **Status:** Accepted
- **Date:** 2026-07-22

## Context

AIEL's single most emphasized rule is that low-confidence decisions must never take autonomous effect, and
that this must be structurally impossible to bypass. AIEL states the gate "is enforced in the agent runtime
class, not in a properties file or database table. Operators cannot disable it by changing configuration"
(`aether-iel/lifecycle/06-implementation.md`), and mandates a `confidence_gate_bypass_total` metric that must
remain zero (`aether-iel/lifecycle/09-governance.md`).

## Decision

The confidence gate is implemented **once, in the harness core**, on the return path of every agent
invocation. It sets `AgentOutput.decision.autoEnforced`. Agents **cannot** set `autoEnforced` (the harness
overwrites it). The default threshold is **0.80**, may be raised per authority level, and **may never be
lowered below 0.80** for any externally-effecting action. There is **no** configuration, flag, environment
variable, or API that disables the gate.

## Rationale

- Centralizing the gate means no agent can bypass it by altering its own output, and the gate logic is in one
  place and independently testable (AIEL Phase 5).
- Making it non-disableable removes the most dangerous operational failure mode (a flag that turns off safety).

## Consequences

- `autoEnforced` is a harness-owned field; the envelope (§2.2) reflects this.
- The harness MUST emit `confidence_gate_bypass_total`; a non-zero value is a critical incident, not a warning.
- Authority-specific thresholds (`RATE_LIMIT` ≥ 0.85, `BLOCK` ≥ 0.95) are encoded in the protocol (§3.1, §4).
