# ADR-0011 — Side-effect gating of tool calls (T-5)

- **Status:** Accepted
- **Date:** 2026-08-08

## Context

The tool registry (ADR-0004) records each tool's declared side-effect class (`none | read | write |
external`, spec §5 T-5), but until now the harness did not *act* on it: a call was authorized against the
allowlist and then executed, regardless of whether it merely read state or performed an irreversible
external write. T-5 requires that "the harness uses side-effect class to decide whether a call is subject
to the confidence gate before execution." The confidence gate (ADR-0003) governs an agent's final
`Decision`, but tool calls happen *during* the agent's run, before any decision exists — so the gate as
written does not cover them.

## Decision

Introduce a **side-effect policy** consulted by the harness at tool-call time, before execution:

- `none`/`read` calls are **ungated** (SE-1).
- `write`/`external` calls are **gated** (SE-2): the caller supplies a per-call `confidence` on the
  `ToolCall`, which MUST clear a per-class threshold (reference defaults `write ≥ 0.85`, `external ≥ 0.95`,
  never below the gate's 0.80 floor).
- A read-only agent (authority `OBSERVE`) MUST NOT perform any gated side effect, at any confidence (SE-3).
- A gated call that fails is **refused before the side effect occurs**, recorded as a `side_effect_denied`
  security event, and resolved to a safe failure default (§8) — never failing open (SE-4).
- Thresholds are configurable via an injected `SideEffectPolicy`; the gating itself cannot be disabled
  (SE-5). It is the tool-call analogue of the confidence gate.

`ToolInvoker.call` gains an optional per-call `confidence` (Python keyword arg; a Java overload). The
spec adds §5.3 and a §9 conformance item.

## Rationale

- Confidence is already the harness's currency for "may this take autonomous effect?"; reusing it for
  side-effecting tool calls keeps one coherent governance model rather than inventing a second axis.
- Enforcing at the bound invoker guarantees the side effect cannot run even if the agent ignores the
  refusal — the guarantee holds regardless of agent behaviour.
- Barring `OBSERVE` agents from writes encodes the intuition that a pure observer must not mutate state.
- A small, focused policy (thresholds only) avoids pulling the full `PolicyPort` (spec §7) forward; that
  general port remains a later increment.

## Consequences

- Existing tools default to `read`, so no current behaviour changes; only tools explicitly declared
  `write`/`external` become gated.
- Agents that call a gated tool must pass a `confidence`; omitting it is treated as `0.0` and refused —
  a safe default that surfaces missing wiring rather than silently executing.
- Both reference implementations (Python + Java) enforce the policy identically, with a shared conformance
  story (`side_effect_denied` security event, safe `DEFER` fallback).
- The broader `PolicyPort` and richer, per-tenant policies remain future work (roadmap Increment 4).
