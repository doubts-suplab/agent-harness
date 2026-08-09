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

Python 3.11+ framework-free core, `bindings/python/src/halo_agent_harness/` (see [ADR-0012](decisions/ADR-0012-bindings-layout.md)).

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
- [x] **Java binding.** `bindings/java/` Maven module (`com.suplab.agentharness:halo-agent-harness`, plain Java 21,
  framework-free) — the Java counterpart to the Python reference: envelope, centralized confidence gate,
  default-deny tool registry, Supervisor+Workers, ports + in-memory adapters, and an
  `interop.LegacyAgentAdapter` for grid. **22 JUnit tests green** (19 conformance + 2 interop + 1 stub) via `mvn test`.
  See [ADR-0009](decisions/ADR-0009-java-binding.md).
- [x] **aether-grid consumes the Java binding.** `aether-agents` depends on `com.suplab.agentharness:halo-agent-harness`;
  the confidence gate is centralized in `HarnessConfidenceGate` (delegating to the harness `ConfidenceGate`),
  deleting the 3 duplicated `0.8` checks (`AgentOutput`, `GovernanceAgent`, `TemporalPredictionAgent`).
  `GovernanceAgent` routes through `Harness.invoke`; BLOCK now auto-enforces at ≥ 0.95. 39 aether-agents tests
  green. Grid docs synced. (Remaining 6 agents migrate incrementally; tool registry is net-new for grid.)
- [x] **eeik-bootstrap consumes the Python runtime (v1.4).** EEIK's generators run on the harness via
  `eeik/generation.py` — a fourth consumer. Generation is modelled as a `SUGGEST`-authority
  agent, so the gate (G-5) guarantees it never auto-enforces: drafts are audited and routed to human
  review, and it fails safe when the harness is absent. See eeik `ADR-003`; `eeik demo` runs it offline.
- [x] **eeik generates Agent Contracts against this spec.** `eeik contract` emits
  `agent-contract.schema.json`-conformant contracts from its blueprints and validates them via this repo's
  own `halo_agent_harness.contract.validate_contract` (schema + §3.3 binding rule). Closes the chain: EEIK
  generates against this repo's Agent Contract schema → HALO runs it. (This schema formalizes the AIEL
  template; AIEL is upstream of HALO, with no dependency on EEIK.) See eeik `ADR-009`.
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
- [x] **Supervisor + Workers — real planning turn (§6.3).** The supervisor is now invoked *through the
  harness* (governed, tool-less): its planning decision passes the gate/kill-switch/audit (O-1), and a
  `BLOCK`/`DEFER` decision **halts delegation** before any worker runs. An optional `Planner` interface
  lets a supervisor select a subset of workers (constrained to the real roster); a plain supervisor
  delegates to all. `OrchestrationResult` gained `supervisor_output`, `delegated`, and `halted`.
  Tests: `tests/test_orchestration_supervisor.py` (6) + `OrchestrationTest` supervisor cases (5).
- [x] **Side-effect gating (T-5, §5.3, ADR-0011).** The harness now consults a tool's side-effect class
  *before execution*. `none`/`read` are ungated; `write`/`external` are gated on a per-call `confidence`
  (defaults `write ≥ 0.85`, `external ≥ 0.95`) and forbidden to read-only (`OBSERVE`) agents. A failed
  gated call is refused pre-effect, logged as a `side_effect_denied` security event, and resolved to a
  safe `DEFER`. Policy thresholds are configurable (`SideEffectPolicy`); the gating cannot be disabled.
  `ToolInvoker.call` gained a per-call `confidence` (Python kwarg / Java overload). Spec §5.2–5.3 + §9
  updated; ADR-0011 added. Tests: `tests/test_side_effect_gating.py` (10) + `SideEffectGatingTest` (9).

**Increment 3 status:** all four orchestration patterns (Pipeline, Fan-out, Debate/Consensus,
Supervisor+Workers with a real planning turn) and side-effect gating are implemented in **both** Python
and Java. Suite: **Python 74 tests**, **Java 54 tests**; `confidence_gate_bypass_total == 0`.

---

## Increment 4 — Production adapters & observability 🚧 (in progress)

Making the "pluggable ports" claim credible with real, optional adapters. The core stays framework-free;
adapters live behind the existing port Protocols and are opt-in.

- [x] **Human-review SLA enforcement + monitoring (§7.4).** `ReviewItem` gained a `deadline` /
  `is_overdue`; the reference queue (`InMemoryHumanReview`) now assigns each item a stable id,
  distinguishes `pending` vs resolved, exposes an `overdue` sweep, and has an audited override endpoint
  (`resolve` → `OverrideRecord`). A new `SlaMonitor` sweeps the queue and emits
  `human_review_sla_breach_total`, counting each breach at most once (idempotent across sweeps).
  Python (`adapters/sla.py`) + Java (`adapters/SlaMonitor.java`). Tests:
  `tests/test_human_review_sla.py` (7) + `HumanReviewSlaTest` (7).
- [x] **Durable append-only file `AuditPort` (§7.3).** `FileAudit` writes one JSON object per line
  (JSONL) in append mode — no update/delete API, PII redacted before every write (INV-4). Read-back
  helpers (`entries`/`security_events` in Python, `lines()` in Java) support inspection; the redactor is
  injectable. Dependency-free (Java uses a small hand-rolled JSON writer). Python
  (`adapters/file_audit.py`) + Java (`adapters/FileAudit.java`). Tests: `tests/test_file_audit.py` (5) +
  `FileAuditTest` (4).
- [x] **Cross-process kill switch (§7.6).** `FileKillSwitch` is engaged iff a shared signal file exists;
  `is_engaged` reads the filesystem each call, so a trip in one process (or an operator's `touch`)
  propagates to every process on the same path. `engage`/`disengage` are idempotent. Proven end-to-end:
  an engaged switch routes every invocation to human review (`DEFER`, never auto-enforced). Python
  (`adapters/file_kill_switch.py`) + Java (`adapters/FileKillSwitch.java`). Tests:
  `tests/test_file_kill_switch.py` (4) + `FileKillSwitchTest` (4).
- [x] **Memory + Policy reference adapters (§7).** `MemoryPort` gains an in-memory and a durable
  file-backed adapter, both **tenant-isolated** by `(tenant_id, user_id, key)` (a scope check rejects
  empty tenant/user). `PolicyPort` gains an immutable `RuleBasedPolicy` (frozen rules — an agent cannot
  loosen them at runtime, INV-3): first matching rule wins, else a configurable default; rules load from
  a durable file. Python (`adapters/memory.py`, `adapters/policy.py`) + Java (`InMemoryMemory`,
  `FileMemory`, `PolicyPort`, `RuleBasedPolicy`). Tests: `tests/test_memory_policy.py` (13) +
  `MemoryPolicyTest` (7).
- [x] **Pluggable richer redaction (§7.3).** Redaction is now a `RedactionStrategy` — an ordered,
  immutable rule set that is *callable* and drops into any port taking a `redactor`. The default covers
  the built-in patterns (JWT/email/card/SSN/phone/key); `with_rule` extends it without mutating the base;
  audit adapters (`InMemoryAudit`, `FileAudit`) accept a custom strategy. The default `redact` free
  function is preserved. Python (`adapters/redaction.py`) + Java (`adapters/RedactionStrategy.java`,
  `Redaction` now a thin facade). Tests: `tests/test_redaction.py` (5) + `RedactionStrategyTest` (4).
- [x] **Production `LlmPort` providers (§7).** One flexible **OpenAI-compatible HTTP adapter**
  (`OpenAICompatibleLlm`) plus a **preset registry** (`PROVIDERS`: OpenAI, Groq, Ollama, Gemini's
  OpenAI-compat endpoint, Sarvam AI) — adding a compatible provider is config, not code
  (`openai_compatible("groq")`). A **native `AnthropicLlm`** covers the Anthropic Messages API
  (top-level system, `input_schema` tools, `text`/`tool_use` blocks). Default transport is an async
  `httpx` client (the `llm` extra; no provider SDKs, lazily imported); keys come from env, and it is
  **offline-tested via an injected transport**; streaming is deferred. Python (`adapters/llm_http.py`,
  `adapters/llm_anthropic.py`). Tests:
  `tests/test_llm_providers.py` (9). *(Python-only this cycle; Java native HTTP LLM adapters are a
  follow-up — the Java binding keeps `StubLlm`.)*
- [x] **OpenTelemetry `ObservabilityPort` exporter (§7.5, §4.2).** `OtelObservability` maps each
  per-invocation metric to an OTel **span** (agent, action, confidence, duration, outcome, correlation
  id) and to **metrics** (`agent_invocations_total` counter + `agent_invocation_duration_ms` histogram),
  and mirrors harness counters — including `confidence_gate_bypass_total` — as OTel counters. It is an
  **optional** adapter (the `otel` extra: `opentelemetry-sdk`), deliberately *not* imported by
  `halo_agent_harness.adapters`, so the SDK is only needed when you import it. Offline-tested with the OTel
  SDK's in-memory span exporter + metric reader, including an end-to-end `Harness` wiring. Python-only
  (`adapters/otel.py`); Java OTel would need a separate optional Maven module (deferred). Tests:
  `tests/test_otel.py` (4).

> **Increment 4 status:** all deliverables except the Prometheus/Grafana metrics dashboard are in
> (that item is deferred). Suite after Increment 4: **Python 121**, **Java 80**.

---

## Increment 5 — Adoption: packaging, examples, standalone docs 🚧 (in progress)

Lowering the barrier for someone outside the Aether family to evaluate and adopt HALO.

- [x] **Standalone README + comparison table.** The README (and `docs/index.html` mirror) now leads with
  *the problem* (agents that act need a governance layer teams otherwise hand-roll), a minimal
  ecosystem-free example, and a **comparison table** vs LangChain/LangGraph, CrewAI, AutoGen, and a raw
  SDK (framed as complementary — governance vs orchestration). The Aether ecosystem is pushed below the
  fold.
- [x] **CHANGELOG.md + versioning/stability policy.** Keep a Changelog format grouped by increment, with
  an explicit `0.x` policy: the protocol may still change pre-1.0, but the safety invariants never weaken;
  1.0 follows a frozen protocol + conformance suite.
- [x] **AGPL-3.0 implications callout + `LICENSING.md`.** A plain-language "what AGPL means if you build
  on HALO" guide (network/§13 copyleft, options, not-legal-advice disclaimer). License unchanged.
- [x] **Agent Contract validation CLI.** `halo validate-contract <path.json>...` (console script +
  `python -m halo_agent_harness`) validates against the schema + binding rule (spec §3.3, §10), with batch
  support and meaningful exit codes (0 valid / 1 invalid / 2 missing). Added two more worked contract
  examples (`observe-monitor`, `advisory-reviewer`). Tests: `tests/test_cli.py` (5).
- [x] **More examples (Python + Java).** Beyond `quickstart`: `orchestration` (all four patterns),
  `contract_validation` (load + validate + the binding rule rejecting a self-escalation), and
  `failure_modes` (agent raises / unauthorized tool / low confidence / kill switch — all resolve to safe
  defaults). Each Python example has a smoke test (`tests/test_examples.py`, 5) so they can't bit-rot; a
  Java `OrchestrationExample` mirrors the orchestration walk-through with its own smoke test.
- [x] **PyPI + Maven Central publish workflows (⧗ external).** Wired but gated on org credentials.
  `publish-python.yml` builds + publishes to PyPI via **Trusted Publishing** (OIDC, no stored token);
  `publish-maven-central.yml` deploys the Java binding via a new pom `release` profile (sources + javadoc +
  GPG sign + Central Publishing plugin, `autoPublish=false` → staged). Central-required pom metadata
  (url/licenses/developers/scm) added; the `release` profile is inactive by default, so `mvn test` is
  unaffected. Verified the Python wheel + sdist build cleanly (incl. the `halo` entry point). Gates
  documented in [`publishing.md`](publishing.md).
- [x] **Public API docs (MkDocs + Javadoc).** Python reference site via MkDocs Material + mkdocstrings
  (`bindings/python/mkdocs.yml` + `apidocs/`, `docs` extra); Java reference via `mvn javadoc:javadoc`.
  A `docs.yml` workflow builds both on every push/PR and deploys the combined site (MkDocs at root,
  Javadoc under `/javadoc`) to GitHub Pages on `main` (deploy gated on Pages being enabled). Both builds
  verified locally.

> **Increment 5 status:** all deliverables in — standalone README + comparison table, CHANGELOG +
> stability policy, AGPL LICENSING.md, contract-validation CLI + more examples, and API docs — plus the
> PyPI/Maven Central publish workflows (⧗ gated on credentials). Suite: **Python 131**, **Java 81**.

---

## Planned next — Increments 4–7

Tracked with feasibility + priority in [`roadmap.md`](roadmap.md):

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
