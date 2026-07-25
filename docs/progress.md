# Progress

Tracks increment-by-increment delivery. Newest first.

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
- [x] **eeik-bootstrap consumes the Python runtime (v1.4).** EEIK's generators run on the harness via
  `eeik/generation.py` — a fourth consumer. Generation is modelled as a `SUGGEST`-authority
  agent, so the gate (G-5) guarantees it never auto-enforces: drafts are audited and routed to human
  review, and it fails safe when the harness is absent. See eeik `ADR-003`; `eeik demo` runs it offline.
- [x] **eeik generates Agent Contracts against this spec.** `eeik contract` emits
  `agent-contract.schema.json`-conformant contracts from its blueprints and validates them via this repo's
  own `agent_harness.contract.validate_contract` (schema + §3.3 binding rule). Closes the chain: AIEL
  specifies → EEIK generates a contract-conformant agent → HALO runs it. See eeik `ADR-009`.
- [ ] Reconcile eeik-bootstrap's three divergent manifest schemas before wide pack rollout
