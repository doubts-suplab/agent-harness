# Project Context — agent-harness

- **What:** Generic, brand-neutral, enterprise-grade agent runtime. The reusable "agent runtime" AIEL
  specifies but does not build. Products consume it; it consumes nothing from them.
- **Repo:** `doubts-suplab/agent-harness` · License AGPL-3.0.
- **Status:** Increment 0 — specification only. No runtime code yet.
- **Reference implementation target:** Python 3.12 (Increment 1).
- **Normative source of truth:** `docs/spec/harness-protocol.md` (+ `docs/spec/agent-contract.schema.json`).
- **Positioning:** methodology (`aether-iel`) → bootstrap (`eeik-bootstrap`) → **runtime (this repo)** → products (`apex-sdlc`, `aether-grid`, `aether-core`).
- **Bootstrap provenance:** seeded from `eeik-bootstrap`; activatable downstream via the `agent-harness` capability pack (ADR-0008).
- **Working branch:** `claude/agent-harness-architecture-y33wmy`.
