# Progress

Tracks increment-by-increment delivery. Newest first. For what's **planned next** (Increments 3–7,
with feasibility and priority), see [`roadmap.md`](roadmap.md).

> **Where things stand:** Increments 0–1 complete; Increment 2 (consumers) nearly complete with one
> open item below. A structured review produced a prioritized plan now tracked in the roadmap:
> (P1) finish orchestration patterns + side-effect gating, (P2) real adapters + observability,
> (P3) packaging + examples + standalone docs, (P4) concurrency/failure tests + finish consumer
> migrations, (P5) cross-language binding + a formal conformance suite. Nothing in Increments 3–7 has
> started yet.

## Increment 0 — Specification ✅ (in review)

Goal: decide the shape of the harness before writing runtime code.

- [x] Normative protocol spec — `docs/spec/harness-protocol.md`
  (envelope, two-axis authority/decision model, confidence gate, tool registry, orchestration, ports,
  failure defaults, conformance checklist)
- [x] Machine-readable Agent Contract schema — `docs/spec/agent-contract.schema.json` (JSON Schema draft-07)
- [x] Worked example contract — `docs/spec/examples/governance-agent.contract.json`
- [x] Decision records — `docs/decisions/ADR-0001..0008`
- [x] Repo scaffold — `CLAUDE.md`, `README.md`, `docs/index.html`, `project-manifest.yaml`, `.claude/` seed
- [x] EEIK integration — `agent-harness` capability pack added to `eeik-bootstrap` (cross-repo, ADR-0008)

## Increment 1 — Python reference implementation ✅ (in review)

Python 3.11+ framework-free core, `src/agent_harness/`. 37 tests green, 94% coverage (runs on 3.11 and 3.12).

- [x] Core: `AgentInput`/`AgentOutput` envelope, two-axis authority/decision model (`core/model.py`)
- [x] Centralized non-disableable confidence gate + bypass counter (`core/gate.py`)
- [x] Default-deny tool registry, no wildcards, security events (`core/registry.py`)
- [x] Harness orchestrator: scope check, kill switch, gate, registry, audit, observability, human review (`core/harness.py`)
- [x] Orchestration: Supervisor + Workers (supervisor holds no tools) (`orchestration/supervisor.py`)
- [x] Ports as Protocols (`ports/llm.py`, `ports/governance.py`) + in-memory reference adapters + LLM stub (`adapters/`)
- [x] Contract loader validating against `agent-contract.schema.json` + semantic binding rule (`contract.py`)
- [x] `pytest` conformance suite mapping 1:1 to spec §9 (`tests/test_conformance.py`) + contract + framework-free tests
- [x] Runnable `examples/quickstart.py`

## Increment 2 — Consumers 🚧 (in progress)

- [x] **apex-sdlc consumes the harness — now all seven phase agents.** apex's phase agents run on the harness
  instead of a hand-rolled loop: `app/agents/` bridge (context mapping, structlog port adapters, `PhaseAgent`
  base, runtime wiring). The full SDLC is implemented on the harness — `RequirementsAgent`,
  `ArchitectureAgent`, `PRReviewerAgent`, `QAAnalystAgent`, `ReleaseEngineerAgent`, `TechWriterAgent`, and
  `ComplianceOfficerAgent` — plus a phase catalog (single source of truth), an in-memory `orchestrator` that
  walks a project through every phase on one harness, and a deterministic stub LLM provider so the whole
  journey runs offline (no DB/keys). A [reference journey](https://github.com/doubts-suplab/apex-sdlc/blob/main/examples/reference-project/README.md)
  demonstrates one project through all 7 phases producing 17 governed artifacts, with the harness (not the
  agents) deciding enforcement and `confidence_gate_bypass_total == 0`. `agent-harness` is a backend
  dependency; **20 bridge/agent/journey tests green** on Python 3.11 (`pytest --noconftest tests/agents/`).
  apex docs/HTML synced (backend + master CLAUDE.md, README, ROADMAP, `docs/personas.md`, reference-journey
  page). Required lowering the harness `requires-python` to 3.11 (ADR-0002 amendment).
- [x] **Java binding.** `java/` Maven module (`com.agentharness:agent-harness-java`, plain Java 21,
  framework-free) — the Java counterpart to the Python reference: envelope, centralized confidence gate,
  default-deny tool registry, Supervisor+Workers, ports + in-memory adapters, and an
  `interop.LegacyAgentAdapter` for grid. **22 JUnit tests green** (19 conformance + 2 interop + 1 stub) via `mvn test`.
  See [ADR-0009](decisions/ADR-0009-java-binding.md).
- [x] **aether-grid consumes the Java binding.** `aether-agents` depends on `com.agentharness:agent-harness-java`;
  the confidence gate is centralized in `HarnessConfidenceGate` (delegating to the harness `ConfidenceGate`),
  deleting the 3 duplicated `0.8` checks (`AgentOutput`, `GovernanceAgent`, `TemporalPredictionAgent`).
  `GovernanceAgent` routes through `Harness.invoke`; BLOCK now auto-enforces at ≥ 0.95. 39 aether-agents tests
  green. Grid docs synced. (Remaining 6 agents migrate incrementally; tool registry is net-new for grid.)
- [ ] Reconcile eeik-bootstrap's three divergent manifest schemas before wide pack rollout
  — carried into [roadmap Increment 6](roadmap.md#increment-6--test-hardening--consumer-migration-p4)
  alongside finishing the remaining aether-grid agent migrations.

---

## Increment 3 — Protocol completeness 🚧 (in progress)

Closing the gap between the normative spec (§6 orchestration, T-5 side-effect gating) and the runtime.
Each pattern is implemented in **both** Python and Java, and every stage/worker still flows through
`Harness.invoke` — so the confidence gate and tool registry apply individually (O-1) and
`confidence_gate_bypass_total` stays 0.

- [x] **Sequential Pipeline (§6.1).** `orchestration/pipeline.py` (Python) + `orchestration/Pipeline.java`
  (Java). Stages run in order; each receives the prior stage's decision in `context["pipeline"]`; the
  pipeline short-circuits on the first `BLOCK`/`DEFER`. `PipelineResult` exposes `final_action`,
  ordered `stage_outputs`, `short_circuited_at`, and a `reconciled_action` (safest action seen).
  Tests: `tests/test_orchestration_pipeline.py` (7) + `OrchestrationTest` pipeline cases (6).
- [x] **Parallel Fan-out (§6.2).** `orchestration/fanout.py` (Python, `ThreadPoolExecutor`) +
  `orchestration/FanOut.java` (Java, fixed thread pool). Independent workers run concurrently over the
  same input; results are collected order-stably and reconciled via the Decision Hierarchy
  (`FanOutResult`). Concurrency is proven by a barrier test in each language; the reference in-memory
  adapters are concurrency-safe (Python: bypass counter now incremented under a lock; Java:
  `CopyOnWriteArrayList` + `ConcurrentHashMap`), so `confidence_gate_bypass_total` accumulates
  correctly. Tests: `tests/test_orchestration_fanout.py` (6) + `OrchestrationTest` fan-out cases (5).
- [x] **Debate / Consensus (§6.4).** `orchestration/debate.py` (Python) + `orchestration/Debate.java`
  (Java). Competing agents produce decisions reconciled by a `ConsensusRule`: `SAFEST` (default —
  strictest action wins per the hierarchy) or `MAJORITY` (plurality; tie → `DEFER`/human review, and
  may de-escalate below the strictest proposal). The **safety floor** is enforced and tested: consensus
  never exceeds the strictest action any participant proposed, nor the strictest participant's authority.
  Added a public `action_precedence`/`Decisions.actionPrecedence` accessor for the §3.3 hierarchy.
  Tests: `tests/test_orchestration_debate.py` (8) + `OrchestrationTest` debate cases (7).

---

## Planned next — Increments 3–7

Not started. Tracked with feasibility + priority in [`roadmap.md`](roadmap.md):

- **Increment 3 (P1) — Protocol completeness:** Pipeline / Fan-out / Debate-Consensus orchestration
  (Python + Java), a real planning turn for Supervisor+Workers, and **side-effect-class gating** so
  the harness consults `tool.side_effect` before execution (T-5).
- **Increment 4 (P2) — Production adapters & observability:** OpenTelemetry exporter, durable audit
  store, real human-review queue + SLA enforcement, production LLM providers, complete Memory/Policy
  ports, cross-process kill-switch, metrics/dashboard.
- **Increment 5 (P3) — Adoption:** standalone (non-Aether) README + comparison table, more
  examples (Python + Java), published API docs, CHANGELOG + stability/deprecation policy, a prominent
  AGPL-3.0 implications note (license unchanged), a contract-validation CLI, and PyPI/Maven Central
  publication (⧗ gated on registry credentials).
- **Increment 6 (P4) — Test hardening & consumer migration:** concurrency/race tests, property-based
  + fuzz, failure-injection E2E, cross-language interop, mutation testing, CI coverage/matrix/badge;
  finish grid agent migrations; close the eeik manifest item.
- **Increment 7 (P5) — Cross-language & formal conformance:** a thin TypeScript binding and a
  language-agnostic conformance suite external implementations can run.

Cross-cutting polish (stricter enforcement surface, configurable hierarchy above the safety floor,
CONTRIBUTING/issue templates, dual-naming consistency) is interleaved. The gate-bypass invariant
(`confidence_gate_bypass_total == 0`) governs every item.
