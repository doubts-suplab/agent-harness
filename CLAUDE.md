# CLAUDE.md — agent-harness Project Brief

> Read this at the start of every session. Single source of truth for what this project is, how it is built, and what rules apply.

---

## What This Project Is

**agent-harness** (`doubts-suplab/agent-harness`) is a **generic, enterprise-grade agent runtime** — the
layer that sits between an agent's decision logic and the outside world and makes agent execution **safe,
governed, observable, and reproducible**.

It is deliberately **brand-neutral**: it depends on no product, imports no product internals, and is not
owned by any single application. It is a generic implementation of the "agent runtime" that the
[Aether Intelligence Engineering Lifecycle (AIEL)](https://github.com/suplab/aether-iel) specifies but does
not build. Products (e.g. apex-sdlc, aether-grid) **consume** it; it consumes nothing from them.

**Capability owned (exclusively):** the *agent execution contract* — the typed I/O envelope, the centralized
confidence gate, the runtime-enforced tool registry, the orchestration patterns, and the pluggable ports.
It does **not** own prompts, business logic, memory content, or product UX.

**Current status:** Increment 0 (spec) + Increment 1 (Python reference implementation) complete. Ships the
normative [harness protocol spec](docs/spec/harness-protocol.md), the
[agent-contract JSON Schema](docs/spec/agent-contract.schema.json), the [decision records](docs/decisions/),
and a Python 3.11+ reference runtime in `src/agent_harness/` (37 tests, 94% coverage). **Increment 2 in
progress:** apex-sdlc consumes the harness (first real consumer). Tests run on Python 3.11 or 3.12
(`python3 -m venv .venv && pip install -e ".[test]" && pytest`).

> **Bootstrapped from EEIK.** This repo follows the `eeik-bootstrap` conventions (CLAUDE.md, `.claude/`,
> `project-manifest.yaml` provenance). It is activatable in downstream projects via the
> `agent-harness` EEIK capability pack. See [ADR-0008](docs/decisions/ADR-0008-eeik-bootstrap-integration.md).

---

## The Four-Layer Positioning

| Layer | Repo | Role |
|---|---|---|
| Methodology / spec | `aether-iel` (AIEL) | Defines the agent contract, authority ladder, confidence gate, governance controls, eval thresholds. Doc-only. |
| Bootstrapping / config | `eeik-bootstrap` | Manifest → capability packs → generators. Not runnable. |
| **Generic agent runtime** | **`agent-harness` ← you are here** | The reusable runtime AIEL references. Brand-neutral. |
| Products / runtimes | `apex-sdlc`, `aether-grid`, `aether-core` | Consume the harness instead of re-implementing agent execution. |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Protocol | Language-neutral specification (Markdown + JSON Schema draft-07) |
| Reference implementation | Python 3.11+ (`src/agent_harness/`) and a Java 21 binding (`java/`, `com.agentharness`) |
| LLM port shape | Adopted from the apex-sdlc provider abstraction (`Message`/`ToolDefinition`/`ToolCall`/`CompletionResult`) |
| Docs | Markdown + a single-page `docs/index.html` mirroring the README |
| License | AGPL-3.0 |

> The harness owns **no** LLM, vector store, or database. All I/O is through ports; concrete adapters live at
> the edge and are supplied by the consumer.

---

## Core Concepts

| Concept | Meaning |
|---|---|
| **AgentInput / AgentOutput** | The typed envelope every invocation consumes/produces (spec §2). |
| **Authority Level** | An agent's static capability ceiling: `OBSERVE < SUGGEST < ALERT < RATE_LIMIT < BLOCK` (spec §3.1). |
| **Decision Action** | The dynamic per-invocation outcome: `ALLOW \| BLOCK \| ALERT \| SUGGEST \| DEFER` (spec §3.2). |
| **Confidence gate** | Centralized, non-disableable runtime check: `confidence < 0.8 → autoEnforced=false → human review` (spec §4). |
| **Tool registry** | Default-deny, runtime-enforced allowlist; no wildcards; violations are security events (spec §5). |
| **Orchestration** | Pipeline, Fan-out, Supervisor+Workers (supervisor holds no tools), Debate (spec §6). |
| **Ports** | LLM, ToolRegistry, Policy, Audit, HumanReview, Observability, Memory, KillSwitch (spec §7). |
| **Agent Contract** | The spec an agent is built from; machine-readable via `agent-contract.schema.json` (spec §10). |

---

## Golden Rules (Non-Negotiable)

These mirror the EEIK golden rules, adapted to a generic runtime:

1. **Constructor injection / explicit wiring** — no hidden global state; adapters are injected.
2. **No hardcoded secrets** — all credentials via environment; never committed.
3. **Structured logging with parameterized messages** — never `print()`/`System.out`.
4. **SOLID + hexagonal** — the core is framework-free; adapters depend on the core, never the reverse.
5. **Ports, not reach-through** — cross-boundary calls go through a port interface.
6. **Explicit column lists / typed queries** in any adapter that touches SQL — never `SELECT *`.
7. **Parameterized queries only** — no string-concatenated SQL.
8. **Conventional Commits** — `type(scope): description`.
9. **No `// TODO` in committed code** — if it's not done, don't commit it.
10. **Spec is normative** — code conforms to `docs/spec/harness-protocol.md`, not the other way around.

### Harness-Specific Constraints (from the protocol)

- The confidence gate lives in the core, runs on every invocation, and **cannot be disabled** (spec §4).
- `autoEnforced` is set by the harness, **never** by an agent.
- Tool access is **default-deny**; allowlists are explicit; **no wildcards**; supervisors hold no tools.
- An agent **cannot** widen its own authority at runtime (no self-escalation).
- Audit is **append-only** and **PII-redacted**; every `BLOCK`/`ALERT` carries a human-readable explanation.
- Every failure resolves to a **safe** decision with lowered confidence and `autoEnforced=false`.
- `confidence_gate_bypass_total` is emitted and MUST stay `0`.

---

## Pre-Coding Checklist

Before writing any code (Increment 1+):
- [ ] Does the change conform to `docs/spec/harness-protocol.md`? Which section?
- [ ] Does it keep the core framework-free (new deps go in adapters, not core)?
- [ ] Does it touch the envelope, gate, registry, or a port contract? → update the spec and an ADR first.
- [ ] Does it change conformance? → update `docs/spec/harness-protocol.md` §9 checklist.
- [ ] Documentation Sync: update `README.md`, `docs/index.html`, `docs/progress.md` as applicable.

---

## Documentation Sync Rule

Every commit that changes behavior or scope MUST keep these in sync:
- `docs/progress.md` — increment status.
- `README.md` — scope/architecture changes.
- `docs/index.html` — mirrors the README (conceptual overview + protocol summary).
- `docs/spec/harness-protocol.md` — any protocol change.
- `docs/decisions/` — a new ADR for any architectural decision.
- **Cross-repo:** a change that also touches `eeik-bootstrap` or a consumer MUST update that repo's docs too.

---

## Prohibited Patterns

- A confidence gate implemented inside an agent (it belongs in the core).
- An agent setting `autoEnforced`.
- Wildcard tool permissions; a supervisor holding tools.
- Runtime authority self-escalation.
- `UPDATE`/`DELETE` on the audit log.
- Failing open into an autonomous action on error.
- The core importing a framework or a concrete adapter.
- Hardcoded secrets; `SELECT *`; string-concatenated SQL; empty catch blocks.
