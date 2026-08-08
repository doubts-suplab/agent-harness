# HALO — agent-harness

[![CI](https://github.com/doubts-suplab/agent-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/doubts-suplab/agent-harness/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![Java 21](https://img.shields.io/badge/Java-21-ED8B00.svg?logo=openjdk&logoColor=white)](java/pom.xml)
[![Tests](https://img.shields.io/badge/tests-Python%2037%20%C2%B7%20Java%2022-brightgreen.svg)](#install--run)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](#status)
[![Spec](https://img.shields.io/badge/spec-normative-6f42c1.svg)](docs/spec/harness-protocol.md)
[![Gate bypass](https://img.shields.io/badge/confidence__gate__bypass__total-0-success.svg)](docs/spec/harness-protocol.md#42-observability-requirement)
[![Version](https://img.shields.io/badge/version-0.1.0-informational.svg)](pyproject.toml)

> **HALO · Harness for Agent Lifecycle & Oversight.** A generic, enterprise-grade agent runtime — a
> language-neutral harness protocol (typed decision envelope, centralized confidence gate, runtime-enforced
> tool registry, composable orchestration, pluggable ports) with Python and Java reference implementations.
> The repo and coordinates stay `agent-harness` / `com.agentharness`; **HALO** is its product identity.

**HALO** is the runtime that stands between an agent's decision logic and the outside world — a *halo* of
oversight (gate, audit, human review, kill switch) around every agent decision. Its job is to make agent
execution **safe, governed, observable, and reproducible** — regardless of which LLM, memory store, or tools
an agent uses, and regardless of host language or framework.

HALO is **vendor-neutral**: it depends on no product and imports no product internals. It is a generic
implementation of the "agent runtime" that the
[Aether Intelligence Engineering Lifecycle (AIEL)](https://github.com/doubts-suplab/aether-iel) specifies but does
not build. It is a first-class peer of the ecosystem's other platforms — **APEX** (SDLC), **EEIK** (bootstrap
kit), and **Aether** (cognitive fabric) — and they **consume** it; it consumes nothing from them.

> **Ecosystem**
>
> | Platform | Repo | Role |
> |---|---|---|
> | **APEX** | [`apex-sdlc`](https://github.com/doubts-suplab/apex-sdlc) | AI-powered SDLC — runs its phase agents on HALO |
> | **EEIK** | [`eeik-bootstrap`](https://github.com/doubts-suplab/eeik-bootstrap) | Bootstrap kit — activates HALO via the `agent-harness` capability pack |
> | **HALO** | `agent-harness` ← **you are here** | Generic agent runtime — the governed execution layer |
> | **Aether** | [`aether-grid`](https://github.com/doubts-suplab/aether-grid) · [`aether-iel`](https://github.com/doubts-suplab/aether-iel) | Cognitive fabric — Grid's agent mesh runs on HALO; AIEL specifies the contract |

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

**Increment 0 — Specification**, **Increment 1 — Python reference**, and **Increment 2 — Java binding +
apex-sdlc consumer** are in. apex-sdlc is the first real consumer and now runs **all seven of its SDLC
phase agents** on the harness (Requirements, Architecture, Development, Testing, CI/CD, Docs, Governance);
its [reference journey](https://github.com/doubts-suplab/apex-sdlc/blob/main/examples/reference-project/README.md)
walks one project through every phase offline, with the harness — not the agents — deciding enforcement.

**Roadmap:** the plan for Increments 3–7 — protocol completeness (remaining orchestration patterns +
side-effect gating), production adapters & observability, adoption (packaging, examples, standalone
docs), test hardening, and cross-language + formal conformance — is tracked with feasibility ratings in
[`docs/roadmap.md`](docs/roadmap.md). Increments 3–7 are planned, not started.

Specification:
- [`docs/spec/harness-protocol.md`](docs/spec/harness-protocol.md) — the normative, language-neutral protocol.
- [`docs/spec/agent-contract.schema.json`](docs/spec/agent-contract.schema.json) — machine-readable Agent Contract schema.
- [`docs/decisions/`](docs/decisions/) — ADR-0001..0009.

Reference implementation — **Python** (`src/agent_harness/`, 3.11+, framework-free core):
- `core/` — envelope, authority/decision model, confidence gate, tool registry, harness.
- `orchestration/` — Supervisor + Workers. `ports/` — LLM + governance Protocols. `adapters/` — in-memory + LLM stub.
- `contract.py` — loads/validates Agent Contracts against the schema.
- `tests/` — 37 tests, 94% coverage, mapping 1:1 to the spec §9 conformance checklist.

**Java** binding (`java/`, `com.agentharness:agent-harness-java`, plain Java 21, framework-free) — the
Java counterpart with the same protocol and §9 checklist, plus an `interop.LegacyAgentAdapter` for the
aether-grid migration. 22 JUnit tests (`cd java && mvn test`). See [ADR-0009](docs/decisions/ADR-0009-java-binding.md).

## Install & run

```bash
python3 -m venv .venv && source .venv/bin/activate   # Python 3.11+
pip install -e ".[test]"        # library + test deps

pytest                          # 37 tests, ~94% coverage
python examples/quickstart.py   # end-to-end demo
```

```python
from agent_harness import AgentInput, Harness      # zero-config: in-memory adapters by default
out = Harness().invoke(my_agent, AgentInput("tenant", "user", context={...}))
# out.decision.auto_enforced was decided by the harness gate — never by the agent
```

The **core** (`core`, `ports`, `orchestration`) has no third-party dependencies. `contract` validation and
the test suite pull `jsonschema`/`pytest` via extras. Next: aether-grid consumes the Java binding (centralize
its duplicated confidence gate). See [`docs/progress.md`](docs/progress.md).

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
