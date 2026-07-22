# Harness Protocol Specification

> **Status:** Draft (Increment 0 — specification). Language-neutral. Normative.
> **Conformance:** An implementation is *harness-conformant* if it satisfies every rule marked **MUST**
> in this document and passes the [Conformance Checklist](#9-conformance-checklist).
> **Provenance:** This protocol is a generic implementation of the "agent runtime" that the
> [Aether Intelligence Engineering Lifecycle (AIEL)](https://github.com/suplab/aether-iel) specifies but
> deliberately does not build. Every normative rule cites its AIEL source. The harness is **brand-neutral**:
> it depends on no Aether product and imports no product internals.

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used per RFC 2119.

---

## 1. Scope and purpose

The **agent harness** is the runtime that stands between an agent's decision logic and the outside world.
Its job is to make agent execution **safe, governed, observable, and reproducible** — regardless of which
LLM, memory store, or tools an agent uses, and regardless of the host language or framework.

The harness owns seven responsibilities:

1. A typed **agent I/O envelope** (§2).
2. A two-axis **authority + decision model** (§3).
3. A centralized, non-disableable **confidence gate** (§4).
4. A runtime-enforced **tool registry** (§5).
5. A set of composable **orchestration patterns** (§6).
6. A set of pluggable **ports** for LLM, memory, audit, human review, observability, policy, and kill-switch (§7).
7. Deterministic **failure-mode defaults** (§8).

It is explicitly **not** the agent's reasoning, prompts, or business logic — those live in the agent
implementation and its Agent Contract (§10). *"Code follows contracts; contracts do not follow code."*
— AIEL Phase 6.

### 1.1 Design invariants (non-negotiable)

These invariants hold in every conformant implementation. Each is elaborated in the referenced section.

- **INV-1 — The gate is in the runtime, not the agent.** No agent can approve its own decision (§4).
- **INV-2 — Tools are default-deny.** A tool not in an agent's registry entry is unreachable (§5).
- **INV-3 — No self-escalation.** An agent cannot widen its own authority at runtime (§3).
- **INV-4 — Every decision is auditable.** Audit is append-only and PII-redacted (§7.3).
- **INV-5 — The core is framework-free.** Adapters depend on the core; the core depends on nothing (§7).

---

## 2. The agent I/O envelope

Every agent invocation consumes exactly one `AgentInput` and produces exactly one `AgentOutput`. This is the
single most reused interface in the system and the boundary at which the harness applies its controls.

> Source: `aether-iel/templates/agent-contract.md` (Input/Output Contract), harmonized with the apex-sdlc
> `AgentContext` / `AgentResult` dataclasses (`apex-sdlc/platform/backend/CLAUDE.md`).

### 2.1 `AgentInput`

| Field | Type | Required | Notes |
|---|---|---|---|
| `tenantId` | string | **MUST** | Multi-tenancy boundary. Every downstream store/query is scoped by it. |
| `userId` | string | **MUST** | Acting principal. |
| `context` | map<string, any> | **MUST** | Task-specific payload (brief, diff, event, etc.). |
| `metadata` | map<string, any> | **MUST** | Non-semantic run metadata (correlationId, runId, source, locale). |

- The harness **MUST** validate that `tenantId` and `userId` are present and non-empty before invoking an
  agent; a missing scope is a rejected invocation, never a defaulted one.
- The harness **MUST** propagate a correlation/trace identifier from `metadata` into every port call (§7.5).

### 2.2 `AgentOutput`

```
AgentOutput {
  decision: Decision
  agentName: string          // MUST match the invoked agent's registered name
  executedAt: timestamp      // MUST be UTC, ISO-8601
}

Decision {
  action: DecisionAction     // §3.2
  confidence: number         // MUST be in [0.0, 1.0]
  rationale: string          // MUST be human-readable; MUST be present for BLOCK/ALERT
  autoEnforced: boolean      // MUST be set by the harness (§4), never by the agent
}
```

- An agent **MUST NOT** set `autoEnforced`. The agent proposes `action`, `confidence`, and `rationale`;
  the **harness** decides `autoEnforced` by running the confidence gate (§4). If an agent returns a value
  for `autoEnforced`, the harness **MUST** overwrite it.
- `confidence` outside `[0.0, 1.0]` is a protocol violation; the harness **MUST** treat it as a runtime
  failure and apply the failure-mode default (§8).

---

## 3. Authority and decision model (two axes)

AIEL describes two overlapping five-valued enumerations that have historically drifted (see
[ADR-0006](../decisions/ADR-0006-decision-envelope-reconciliation.md)). This protocol keeps **both**, on
**separate axes**, and defines how they relate. Conflating them is the drift; separating them is the fix.

### 3.1 Authority Level — the *capability ceiling* of an agent (static)

Declared once per agent in its Agent Contract; **MUST NOT** change at runtime (INV-3).

| Level | Name | Meaning | Min confidence to auto-enforce |
|---|---|---|---|
| 1 | `OBSERVE` | Read-only, no external effect | n/a (never enforces) |
| 2 | `SUGGEST` | Recommendation for a human | always human-reviewed |
| 3 | `ALERT` | Raises a flag in observability | ≥ 0.80 |
| 4 | `RATE_LIMIT` | Throttles/degrades a target | ≥ 0.85 |
| 5 | `BLOCK` | Rejects/terminates an action | ≥ 0.95 |

> Source: `aether-iel/lifecycle/05-agent-engineering.md` (Authority Levels).

### 3.2 Decision Action — the *outcome of one invocation* (dynamic)

Emitted per invocation in `Decision.action`.

`ALLOW | BLOCK | ALERT | SUGGEST | DEFER`

> Source: `aether-iel/templates/agent-contract.md` (Capabilities enum).

### 3.3 The binding rule

- An agent **MUST NOT** emit a `DecisionAction` whose enforcement effect exceeds its Authority Level.
  The harness **MUST** reject an out-of-authority action and apply the failure-mode default (§8). Mapping:

  | DecisionAction | Requires Authority ≥ |
  |---|---|
  | `ALLOW` | any (no external effect) |
  | `SUGGEST` | `SUGGEST` |
  | `ALERT` | `ALERT` |
  | `DEFER` | any (routes to human; no autonomous effect) |
  | `BLOCK` | `BLOCK` |

- `DEFER` is the explicit "I decline to decide — send to a human" outcome. It is always safe and **MUST**
  route to the human review queue (§7.4) regardless of confidence.
- The Decision Hierarchy for conflict resolution across multiple agents is
  `BLOCK > RATE_LIMIT > ALERT > SUGGEST > DEFER > ALLOW`.
  > Source: `aether-iel/standards/governance-controls.md` §2.1.

---

## 4. The confidence gate

The confidence gate is the heart of the harness. It is the mechanism by which the system guarantees that
low-confidence decisions never take autonomous effect.

> Source: `aether-iel/lifecycle/05-agent-engineering.md` and `06-implementation.md`
> ("Confidence gate is code, not configuration"); `standards/governance-controls.md` §2.1.

### 4.1 Rules

- **G-1 (INV-1).** The gate **MUST** be implemented once, in the harness core, and run on the return path of
  every agent invocation. It **MUST NOT** be implemented inside individual agents.
- **G-2.** Default threshold is **0.80**. If `confidence < threshold`, the harness **MUST** set
  `autoEnforced = false` and route the decision to the human review queue (§7.4) with full context.
- **G-3.** The threshold **MAY** be raised per authority level (§3.1: `RATE_LIMIT` ≥ 0.85, `BLOCK` ≥ 0.95)
  but **MUST NOT** be lowered below 0.80 for any action that produces an external effect.
- **G-4.** The gate **MUST NOT** be disableable by configuration, environment variable, feature flag, or API.
  There is no "gate off" state. (AIEL: the `autoEnforced=false` rule "is enforced in the agent runtime class,
  not in a properties file or database table. Operators cannot disable it.")
- **G-5.** `SUGGEST`-authority and `OBSERVE`-authority agents never auto-enforce; the gate **MUST** set
  `autoEnforced = false` for them irrespective of confidence.

### 4.2 Observability requirement

- The harness **MUST** emit a counter `confidence_gate_bypass_total`. Its value **MUST** be permanently `0`
  in any correct deployment; a non-zero value is a critical governance incident.
  > Source: `aether-iel/lifecycle/09-governance.md`.
- The harness **MUST** emit, per invocation, a record carrying: agent name, action, confidence, duration,
  and outcome (`auto-enforced` vs `human-review`). (§7.5)

---

## 5. The tool registry

The tool registry is the **governance boundary for agent capabilities**. "A tool not in the registry does
not exist from the agent's perspective." — AIEL Phase 5.

> Source: `aether-iel/lifecycle/05-agent-engineering.md`, `09-governance.md`;
> `standards/governance-controls.md` §2.1 (non-negotiable #4).

### 5.1 Rules

- **T-1 (INV-2).** Tool access is **default-deny**. Each agent has an explicit allowlist of tool names in its
  Agent Contract. A tool call whose name is not in that allowlist **MUST** be refused by the harness before
  any side effect occurs.
- **T-2.** A refused tool call **MUST** be logged as a **security event** (§7.3) and **MUST NOT** be silenced.
- **T-3.** Wildcards are forbidden. An allowlist **MUST** enumerate concrete tool names; `"*"` or prefix
  globs are a protocol violation.
  > Source: `aether-iel/standards/governance-controls.md` §2.1 ("Tool access list is explicit (no wildcard permissions)").
- **T-4.** A **supervisor** agent (§6.3) **MUST** hold an empty tool allowlist — it coordinates, it does not act.
- **T-5.** Each registry entry **MUST** record the tool's name, description, JSON-Schema parameters, and
  declared side-effect class (`none | read | write | external`). The harness uses side-effect class to decide
  whether a call is subject to the confidence gate before execution.

### 5.2 Tool call shape

Tool definitions and calls reuse the shape already proven in the apex-sdlc LLM provider layer
(`apex-sdlc/platform/backend/app/integrations/llm/base.py`) so adapters map 1:1:

```
ToolDefinition { name, description, parameters: JSONSchema, sideEffect: none|read|write|external }
ToolCall       { name, arguments: map, id }
```

---

## 6. Orchestration patterns

The harness provides four composable patterns. An orchestration is itself framework-free: it sequences
agent invocations and reconciles their `Decision`s using the Decision Hierarchy (§3.3).

> Source: `aether-iel/lifecycle/05-agent-engineering.md` (Agent Interaction).

### 6.1 Sequential Pipeline
Agents run in order; each receives the prior stage's output in its `context`. First `BLOCK`/`DEFER`
short-circuits per the hierarchy.

### 6.2 Parallel Fan-out
Agents run concurrently over the same `AgentInput`; the harness reconciles their decisions with the
Decision Hierarchy (`BLOCK` wins, then `RATE_LIMIT`, …).

### 6.3 Supervisor + Workers *(primary pattern for complex tasks)*
A supervisor agent plans and delegates to worker agents. **The supervisor holds no tool permissions**
(T-4) — it coordinates only; workers do the acting. This is the recommended default for multi-step tasks.

### 6.4 Debate / Consensus
Multiple agents produce competing decisions; a consensus rule (or a supervisor) reconciles them. Ties
resolve toward the safer action per the hierarchy.

- **O-1.** Every agent invocation inside any orchestration **MUST** pass through the confidence gate (§4)
  and tool registry (§5) individually. Orchestration composes agents; it does not bypass their controls.

---

## 7. Ports (hexagonal boundary)

The harness core is framework-free (INV-5). All I/O is expressed through ports (interfaces); concrete
adapters (Anthropic, pgvector, Postgres audit, a queue, OpenTelemetry, …) are supplied at the edge and
depend on the core, never the reverse.

> The `LlmPort` shape is adopted verbatim from `apex-sdlc/platform/backend/app/integrations/llm/base.py`
> (`Message`, `ToolDefinition`, `ToolCall`, `CompletionResult`, `LLMProvider` Protocol), which already
> abstracts Anthropic/Groq/Ollama/HuggingFace.

| Port | Responsibility | Key rule |
|---|---|---|
| `LlmPort` | `complete(messages, system, tools, …) -> CompletionResult`; `stream(...)` | Provider-agnostic; selected by config. No agent calls an SDK directly. |
| `ToolRegistryPort` | Resolve + authorize tool calls for an agent | Default-deny (§5). |
| `PolicyPort` | Evaluate authority + action against immutable rules | Rules are immutable at runtime; no self-escalation (INV-3). |
| `AuditPort` | Append-only decision + security-event log | See §7.3. |
| `HumanReviewPort` | Enqueue low-confidence / `DEFER` / `SUGGEST` decisions | See §7.4. |
| `ObservabilityPort` | Per-invocation metrics + trace context | See §7.5. |
| `MemoryPort` | Scoped read/write of agent-visible memory | Every call scoped by `tenantId` (+ collection/team where applicable). |
| `KillSwitchPort` | System-wide stop without a code deploy | See §7.6. |

### 7.3 Audit (append-only, PII-redacted)
- The `AuditPort` log **MUST** be append-only (no UPDATE/DELETE).
- Every `BLOCK`/`ALERT` decision **MUST** carry a human-readable explanation.
- PII **MUST** be redacted before any audit write (email/phone/card/SSN/JWT/API-key patterns). Zero PII in
  logs is a P1 condition.
  > Source: `aether-iel/standards/governance-controls.md` §2.2.

### 7.4 Human review queue
- Low-confidence (§4), `DEFER`, and `SUGGEST` decisions **MUST** be enqueued with full context.
- Entries **MUST** carry an SLA; the reference SLAs are 1h for `BLOCK`-level, 4h for `ALERT`-level.
- A human override endpoint **MUST** exist; overrides are themselves audited.
  > Source: `aether-iel/lifecycle/09-governance.md`.

### 7.5 Observability
- The harness **MUST** propagate trace context (correlation id from `AgentInput.metadata`) into every port call.
- It **MUST** emit, per invocation: agent, action, confidence, duration, outcome; plus the
  `confidence_gate_bypass_total` counter (§4.2).

### 7.6 Kill switch
- The system **MUST** be stoppable without a code deployment. When the kill switch is engaged, the harness
  **MUST** refuse all auto-enforcing actions and route everything to human review.
  > Source: `aether-iel/standards/governance-controls.md` §2.3.

---

## 8. Failure-mode defaults

Every failure resolves to a **safe** decision with lowered confidence and `autoEnforced = false`. The agent
never "fails open" into an autonomous action.

> Source: `aether-iel/templates/agent-contract.md` §10 (Failure Behaviour).

| Failure | Default decision |
|---|---|
| LLM unavailable / timeout | `ALLOW`, `confidence = 0.5`, `autoEnforced = false` |
| Memory store timeout | `DEFER`, `confidence = 0.6` |
| Missing required context | `DEFER`, `confidence = 0.5` |
| Tool failure | `DEFER`, `confidence = 0.6`, security event if authorization-related |
| Unexpected output shape / confidence out of range | `DEFER`, `confidence = 0.0` |
| Out-of-authority action (§3.3) | downgrade to `DEFER`, security event |

- **F-1.** Every agent's Agent Contract **MUST** enumerate its failure modes; the harness applies the table
  above as the default when a contract is silent.

---

## 9. Conformance checklist

An implementation is conformant only if all of the following hold. These are lifted from
`aether-iel/standards/evaluation-criteria.md` and `standards/governance-controls.md`.

- [ ] **Envelope.** Exactly one `AgentInput` in, one `AgentOutput` out; `tenantId`/`userId` validated (§2).
- [ ] **Gate centralized.** Confidence gate runs in the core on every invocation; not in agents (INV-1, §4).
- [ ] **Gate non-disableable.** No config/flag/API can turn the gate off (G-4).
- [ ] **Low-confidence routing = 100%.** Every `confidence < threshold` decision reaches human review.
- [ ] **Gate bypass = 0.** `confidence_gate_bypass_total` is emitted and stays at 0 (§4.2).
- [ ] **Tools default-deny.** Out-of-allowlist calls refused pre-effect and logged as security events (INV-2, §5).
- [ ] **No wildcards.** Tool allowlists are explicit (T-3).
- [ ] **Supervisor holds no tools.** (T-4)
- [ ] **No self-escalation.** Authority is static per contract (INV-3).
- [ ] **Audit append-only + PII-redacted.** BLOCK/ALERT carry explanations (INV-4, §7.3).
- [ ] **Kill switch.** System stoppable without deploy (§7.6).
- [ ] **Safe failure defaults.** All failure paths lower confidence and set `autoEnforced=false` (§8).
- [ ] **Core is framework-free.** Adapters depend on core, not vice versa (INV-5, §7).

---

## 10. The Agent Contract

Each agent is defined by an **Agent Contract** — the specification *from which implementation follows*.
"An agent without a contract does not get built." — AIEL Phase 5.

The machine-readable schema is [`agent-contract.schema.json`](./agent-contract.schema.json). A contract
declares: Identity, Authority Level (§3.1), Capabilities (allowed `DecisionAction`s), Confidence gate,
Tool access allowlist (§5), Input/Output contract (§2), Fast-path conditions, Failure behaviour (§8),
Testing requirements, and Governance sign-off. The harness **MUST** load and validate every contract at
startup and **MUST** refuse to run an agent whose contract fails schema validation.

---

## 11. Appendix — consumer adapter sketches (non-normative)

Illustrative only; no code is shipped in this increment.

- **apex-sdlc (Python).** apex's spec'd `AgentContext{project_id, phase, actor_id, inputs, …}` maps onto
  `AgentInput` (`tenantId ← org/tenant`, `userId ← actor_id`, `context ← inputs`, `metadata ← {run_id, phase}`);
  `AgentResult{status, artifacts, token_usage, cost_usd}` becomes port-side observability plus an `AgentOutput`
  whose `Decision` defaults to `ALLOW` for generative phases. apex's PII guard and audit middleware become the
  `AuditPort` adapter; its `integrations/llm/` factory becomes the `LlmPort` adapter.
- **aether-grid (Java).** grid's `Agent` SPI + `AgentOrchestrator` map onto §2 + §6; its `GovernanceAgent`
  confidence handling becomes a thin agent atop the core gate (§4) rather than a bespoke re-implementation.
