# HALO — agent-harness

[![CI](https://github.com/doubts-suplab/agent-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/doubts-suplab/agent-harness/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](bindings/python/pyproject.toml)
[![Java 21](https://img.shields.io/badge/Java-21-ED8B00.svg?logo=openjdk&logoColor=white)](bindings/java/pom.xml)
[![Tests](https://img.shields.io/badge/tests-Python%20121%20%C2%B7%20Java%2080-brightgreen.svg)](#install--run)
[![Orchestration](https://img.shields.io/badge/orchestration-4%20patterns-6f42c1.svg)](docs/spec/harness-protocol.md#6-orchestration-patterns)
[![Spec](https://img.shields.io/badge/spec-normative-6f42c1.svg)](docs/spec/harness-protocol.md)
[![Gate bypass](https://img.shields.io/badge/confidence__gate__bypass__total-0-success.svg)](docs/spec/harness-protocol.md#42-observability-requirement)

[![Version](https://img.shields.io/badge/version-0.1.0-informational.svg)](CHANGELOG.md)

> **HALO · Harness for Agent Lifecycle & Oversight.** A vendor-neutral runtime that governs what your AI
> agents are allowed to *do* — a confidence gate, a default-deny tool registry, audit, human review, and a
> kill switch around every agent decision. Language-neutral protocol; Python and Java reference bindings.

---

## The problem

An LLM agent that only *answers* is low-stakes. An agent that **acts** — refunds a payment, closes a
ticket, merges a PR, emails a customer — is not. The moment agents take real actions, every team ends up
hand-rolling the same governance layer:

- "Only auto-apply this if the model is confident enough — otherwise send it to a human."
- "This agent may *flag* risk but must never *block*."
- "An agent can only call the three tools on its allowlist — nothing else, ever."
- "Every decision must be audited, with PII stripped, and we need a way to stop everything without a deploy."

**HALO is that layer, built once and done right.** It sits between an agent's decision logic and the
outside world and makes agent execution **safe, governed, observable, and reproducible** — regardless of
which LLM, memory store, or tools the agent uses, and regardless of host language or framework. It owns the
*execution contract*, not your prompts or business logic.

It is defined by a [normative, language-neutral protocol](docs/spec/harness-protocol.md) with a
[machine-readable conformance checklist](docs/spec/harness-protocol.md#9-conformance-checklist); the Python
and Java bindings both implement it identically.

## What HALO gives you

1. A typed **agent I/O envelope** — one `AgentInput` in, one `AgentOutput` out; every call scoped by tenant + user.
2. A two-axis **authority + decision** model — a static capability *ceiling* per agent vs. the dynamic *outcome* of one call.
3. A centralized, **non-disableable confidence gate** — `confidence < 0.8 → not auto-enforced → human review`. The agent never decides this; the harness does.
4. A runtime-enforced, **default-deny tool registry** — explicit allowlists, no wildcards, violations are security events; `write`/`external` tool calls are gated on confidence *before they run*.
5. Composable **orchestration** — Pipeline, Fan-out, Debate/Consensus, and Supervisor+Workers (the supervisor holds no tools).
6. Pluggable **ports** — LLM, ToolRegistry, Policy, Audit, HumanReview, Observability, Memory, KillSwitch — with reference adapters (in-memory, durable file, OpenTelemetry, OpenAI-compatible/Anthropic LLMs).
7. Deterministic **failure-mode defaults** — every failure resolves to a safe, non-enforcing decision. It never fails open.

## Minimal example

No ecosystem, no config — an agent is any object with a name, an authority ceiling, the decisions it may
emit, and a `run` method:

```python
from agent_harness import AgentInput, AuthorityLevel, Decision, DecisionAction, Harness


class RefundApprover:
    name = "refund-approver"
    authority_level = AuthorityLevel.BLOCK                      # its capability ceiling
    capabilities = frozenset({DecisionAction.ALLOW, DecisionAction.BLOCK})

    def run(self, request: AgentInput, tools) -> Decision:
        amount = request.context["amount"]
        if amount > 1000:
            return Decision(DecisionAction.BLOCK, confidence=0.99, rationale="over policy limit")
        return Decision(DecisionAction.ALLOW, confidence=0.75, rationale="within policy")


harness = Harness()   # zero-config: in-memory reference adapters

high = harness.invoke(RefundApprover(), AgentInput("acme", "u1", context={"amount": 5000}))
print(high.decision.action, high.decision.auto_enforced)   # BLOCK True  — confident + within authority

low = harness.invoke(RefundApprover(), AgentInput("acme", "u1", context={"amount": 20}))
print(low.decision.action, low.decision.auto_enforced)     # ALLOW False — 0.75 < 0.8 → routed to a human
```

`auto_enforced` was decided by the **harness gate**, never by the agent — and the low-confidence ALLOW was
automatically queued for human review. That inversion of control is the whole point.

## How HALO compares

HALO is a **governance/oversight** layer, not another way to *build* or *orchestrate* agents — so it is
**complementary** to the frameworks below. You can build an agent with LangGraph, CrewAI, or a raw SDK and
run it *under* HALO to get the gate, registry, audit, and kill switch.

| Capability | **HALO** | LangChain / LangGraph | CrewAI | AutoGen | Raw provider SDK |
|---|:--:|:--:|:--:|:--:|:--:|
| Primary focus | Governance & oversight | Building & orchestration | Role-based multi-agent | Conversational multi-agent | Model calls + tool-use |
| Centralized, non-disableable confidence gate | ✅ | DIY | DIY | DIY | — |
| Default-deny tool registry enforced by the runtime | ✅ | DIY | DIY | DIY | — |
| Static authority ceiling vs. dynamic decision | ✅ | — | — | — | — |
| Append-only, PII-redacted audit | ✅ | DIY | DIY | DIY | — |
| Human-review queue with SLA enforcement | ✅ | DIY | DIY | partial (HITL) | — |
| System-wide kill switch (no deploy) | ✅ | — | — | — | — |
| Safe failure defaults (never fails open) | ✅ | DIY | DIY | DIY | — |
| Language-neutral normative spec + conformance | ✅ | — | — | — | — |
| Vendor / framework neutral | ✅ | Py/JS ecosystem | Python | Python | single vendor |

> ✅ first-class and enforced by the runtime · DIY achievable by wiring it yourself · partial available but limited · — not a focus.
> Comparisons reflect each project's primary design intent, not a claim that the others *cannot* be extended.

## Install & run

```bash
cd bindings/python
python3 -m venv .venv && source .venv/bin/activate    # Python 3.11+
pip install -e ".[test]"         # library + test deps

pytest                           # 121 tests, mapping to the §9 conformance checklist
python examples/quickstart.py    # end-to-end demo
```

The **core** (`core`, `ports`, `orchestration`) has **no third-party dependencies** — it is framework-free
by design. Optional adapters live behind extras: `contract` (schema validation), `llm` (OpenAI-compatible +
Anthropic providers), `otel` (OpenTelemetry). Java: `cd bindings/java && mvn test` (80 JUnit tests).

## Repository layout

The protocol is language-neutral; each implementation is a peer **binding** under `bindings/`, with the
normative spec and decision records shared at the root ([ADR-0012](docs/decisions/ADR-0012-bindings-layout.md)):

```
docs/spec/        normative protocol + Agent Contract schema (canonical, language-neutral)
docs/decisions/   ADRs
bindings/python/  Python reference binding (src/, tests/, examples/, pyproject.toml)
bindings/java/    Java binding (src/, pom.xml)
```

## Status

Increments 0–3 are in; Increment 4 (production adapters) is largely delivered:

- **0 — Specification** · **1 — Python reference** · **2 — Java binding + apex-sdlc consumer.**
- **3 — Protocol completeness** (both languages): all four orchestration patterns + side-effect gating (T-5, §5.3).
- **4 — Production adapters** (in progress): human-review SLA monitoring, durable file audit, cross-process
  kill switch, Memory/Policy adapters, pluggable redaction, OpenTelemetry exporter, and OpenAI-compatible +
  Anthropic LLM providers.

Full detail in [`docs/progress.md`](docs/progress.md); the forward plan (Increments 5–7) with feasibility
ratings is in [`docs/roadmap.md`](docs/roadmap.md).

## Reading order

1. [`docs/spec/harness-protocol.md`](docs/spec/harness-protocol.md) — the normative, language-neutral protocol. Start here.
2. [`docs/decisions/`](docs/decisions/) — ADR-0001..0012: why the protocol is shaped this way.
3. [`docs/spec/agent-contract.schema.json`](docs/spec/agent-contract.schema.json) — the contract an agent is built from.

---

## Where it fits — the Aether ecosystem

HALO is useful entirely on its own. It also happens to be the generic runtime that the **Aether
Intelligence Engineering Lifecycle (AIEL)** specifies but does not build — so the ecosystem's platforms
**consume** it (it consumes nothing from them):

| Platform | Repo | Role |
|---|---|---|
| **APEX** | [`apex-sdlc`](https://github.com/doubts-suplab/apex-sdlc) | AI-powered SDLC — runs all seven of its phase agents on HALO |
| **EEIK** | [`eeik-bootstrap`](https://github.com/doubts-suplab/eeik-bootstrap) | Bootstrap kit — activates HALO via the `agent-harness` capability pack |
| **HALO** | `agent-harness` ← **you are here** | Generic agent runtime — the governed execution layer |
| **Aether** | [`aether-grid`](https://github.com/doubts-suplab/aether-grid) · [`aether-iel`](https://github.com/doubts-suplab/aether-iel) | Cognitive fabric — Grid's agent mesh runs on HALO; AIEL specifies the contract |

Before `agent-harness`, every one of these hand-rolled the same shape — typed envelope → confidence gate →
tool registry → orchestration → audit. This repo makes that a single, conformant, reusable runtime.

This repo also follows `eeik-bootstrap` conventions (`CLAUDE.md`, `.claude/`, `project-manifest.yaml`) and is
activatable downstream via the **`agent-harness` EEIK capability pack** ([ADR-0008](docs/decisions/ADR-0008-eeik-bootstrap-integration.md)).

## License

AGPL-3.0 — see [LICENSE](LICENSE) and, for what that means if you build on HALO, [LICENSING.md](LICENSING.md).
