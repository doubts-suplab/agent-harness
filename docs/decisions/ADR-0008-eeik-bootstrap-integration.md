# ADR-0008 — The harness is activated via an EEIK `agent-harness` capability pack

- **Status:** Accepted
- **Date:** 2026-07-22

## Context

`eeik-bootstrap` is the ecosystem's bootstrapping layer: a project's `project-manifest.yaml` drives capability
packs, agent blueprints, and generators (`/bootstrap → /validate-manifest → /generate-repo`). For the harness
to be adoptable "for free" by any new AI/agent project, it must be discoverable and activatable through that
same manifest-driven flow — not bolted on by hand.

## Decision

Ship a first-class **`agent-harness` capability pack** in `eeik-bootstrap`
(`capability-packs/agent-harness/`), mirroring the existing pack format
(`capability-packs/java/metadata.yaml`). The pack:

- triggers on manifests with `ai.pattern in [multi-agent, agent]` (or `ai.enabled: true`);
- provides the `agent-harness-protocol` standard (a condensed conformance summary linking to this repo's
  full [`harness-protocol.md`](../spec/harness-protocol.md));
- points at `doubts-suplab/agent-harness` as the reference runtime.

The pack is a **complement** to this repo (ADR-0001), not a substitute: the pack describes and recommends the
harness; this repo *is* the harness spec and (from Increment 1) its reference implementation.

## Rationale

- Makes the harness part of the standard bootstrap story for AI projects.
- Keeps the runtime in a neutral repo while keeping activation in the bootstrap kit — separation of concerns.

## Consequences

- Cross-repo change: `eeik-bootstrap` gains the pack, a `capability-matrix.yaml` trigger row, and doc updates
  (README, CLAUDE.md, pack catalogue) per its Documentation Sync Rule.
- Provenance is recorded both ways: this repo's `project-manifest.yaml` records `source: eeik-bootstrap`; the
  eeik pack links back to this repo.
