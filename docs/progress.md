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

## Increment 2 — Consumers 🔜 (planned)

- [ ] apex-sdlc consumes the harness (replaces its hand-rolled `BaseAgent`); update apex docs/HTML
- [ ] Java binding for aether-grid; update grid docs/HTML
- [ ] Reconcile eeik-bootstrap's three divergent manifest schemas before wide pack rollout
