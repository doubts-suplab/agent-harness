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

## Increment 1 — Python reference implementation 🔜 (planned)

- [ ] Core: `AgentInput`/`AgentOutput` envelope, confidence gate, tool registry
- [ ] Orchestration: Supervisor + Workers (primary pattern) first
- [ ] Ports + in-memory reference adapters (LLM stub, audit, human-review, observability)
- [ ] `pytest` conformance suite mapping 1:1 to the spec §9 checklist
- [ ] Contract loader that validates against `agent-contract.schema.json` at startup

## Increment 2 — Consumers 🔜 (planned)

- [ ] apex-sdlc consumes the harness (replaces its hand-rolled `BaseAgent`); update apex docs/HTML
- [ ] Java binding for aether-grid; update grid docs/HTML
- [ ] Reconcile eeik-bootstrap's three divergent manifest schemas before wide pack rollout
