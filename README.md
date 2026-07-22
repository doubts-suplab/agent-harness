# agent-harness

> **Generic, enterprise-grade agent runtime.** A language-neutral harness protocol — typed decision
> envelope, centralized confidence gate, runtime-enforced tool registry, composable orchestration, and
> pluggable ports — with a Python reference implementation to come.

`agent-harness` is the runtime that stands between an agent's decision logic and the outside world. Its job
is to make agent execution **safe, governed, observable, and reproducible** — regardless of which LLM, memory
store, or tools an agent uses, and regardless of host language or framework.

It is **brand-neutral**: it depends on no product and imports no product internals. It is a generic
implementation of the "agent runtime" that the
[Aether Intelligence Engineering Lifecycle (AIEL)](https://github.com/suplab/aether-iel) specifies but does
not build. Products **consume** it; it consumes nothing from them.

---

## Where it fits

| Layer | Repo | Role |
|---|---|---|
| Methodology / spec | `aether-iel` (AIEL) | Agent contract, authority ladder, confidence gate, governance controls, eval thresholds. Doc-only. |
| Bootstrapping / config | `eeik-bootstrap` | Manifest → capability packs → generators. Not runnable. |
| **Generic agent runtime** | **`agent-harness` ← this repo** | The reusable runtime AIEL references. Brand-neutral. |
| Products / runtimes | `apex-sdlc`, `aether-grid`, `aether-core` | Consume the harness instead of re-implementing agent execution. |

Before `agent-harness`, every product hand-rolled the same shape — typed envelope → confidence gate → tool
registry → orchestration → audit. This repo makes that a single, conformant, reusable runtime.

---

## What the harness owns

1. A typed **agent I/O envelope** — one `AgentInput` in, one `AgentOutput` out.
2. A two-axis **authority + decision** model — static capability ceiling vs. dynamic per-invocation outcome.
3. A centralized, **non-disableable confidence gate** — `confidence < 0.8 → autoEnforced=false → human review`.
4. A runtime-enforced, **default-deny tool registry** — explicit allowlists, no wildcards, violations are security events.
5. Composable **orchestration** — Pipeline, Fan-out, Supervisor+Workers (supervisor holds no tools), Debate.
6. Pluggable **ports** — LLM, ToolRegistry, Policy, Audit, HumanReview, Observability, Memory, KillSwitch.
7. Deterministic **failure-mode defaults** — every failure resolves to a safe, non-enforcing decision.

It does **not** own prompts, business logic, memory content, or product UX.

---

## Status

**Increment 0 — Specification.** This repo currently ships:

- [`docs/spec/harness-protocol.md`](docs/spec/harness-protocol.md) — the normative, language-neutral protocol.
- [`docs/spec/agent-contract.schema.json`](docs/spec/agent-contract.schema.json) — machine-readable Agent Contract schema.
- [`docs/spec/examples/`](docs/spec/examples/) — a worked contract that validates against the schema.
- [`docs/decisions/`](docs/decisions/) — ADR-0001..0008.
- [`docs/progress.md`](docs/progress.md) — increment tracking.

**No runtime code yet.** Increment 1 is the Python 3.12 reference implementation of the core (envelope, gate,
registry, Supervisor+Workers orchestration, audit/observability ports) plus a conformance test suite.

---

## Reading order

1. [`docs/spec/harness-protocol.md`](docs/spec/harness-protocol.md) — start here.
2. [`docs/decisions/`](docs/decisions/) — why the protocol is shaped this way.
3. [`docs/spec/agent-contract.schema.json`](docs/spec/agent-contract.schema.json) — the contract an agent is built from.

## Bootstrapping

This repo follows `eeik-bootstrap` conventions (`CLAUDE.md`, `.claude/`, `project-manifest.yaml` provenance)
and is activatable in downstream AI/agent projects via the **`agent-harness` EEIK capability pack**. See
[ADR-0008](docs/decisions/ADR-0008-eeik-bootstrap-integration.md).

## License

AGPL-3.0. See [LICENSE](LICENSE).
