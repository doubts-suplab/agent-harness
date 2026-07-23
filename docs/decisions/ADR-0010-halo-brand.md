# ADR-0010 — Brand the harness as HALO (product identity), keep `agent-harness` coordinates

- **Status:** Accepted
- **Date:** 2026-07-23

## Context

Earlier ADRs (0001, 0003) positioned the harness as "brand-neutral." In practice the runtime had no product
identity, while its ecosystem peers do — **APEX** (AI-powered SDLC), **EEIK** (bootstrap kit), **Aether**
(cognitive fabric). Consumers now depend on it (apex-sdlc runs all seven phase agents on it; aether-grid
routes its agent mesh through it), so it deserves a first-class, memorable identity to be referenced and
linked as a peer platform.

## Decision

The harness carries the product/brand name **HALO — "Harness for Agent Lifecycle & Oversight."** The metaphor
is a *halo* of oversight (confidence gate, audit, human review, kill switch) around every agent decision.

- **Repository and Maven/PyPI-style coordinates are unchanged**: the repo stays `agent-harness`, the Java
  artifact stays `com.agentharness:agent-harness-java`, the Python package stays `agent_harness`. HALO is a
  display identity, not a rename — this avoids breaking the just-published binding and downstream consumers.
- "Brand-neutral" is re-framed to **"vendor-neutral"**: HALO depends on no product and is not owned by any
  single application, but it *does* have its own identity.
- HALO is cross-linked into the ecosystem navigation of the peer repos (eeik-bootstrap, apex-sdlc) and carries
  an ecosystem table of its own in the README/landing page.

## Rationale

- A named platform is easier to reference, adopt, and reason about than an anonymous "agent-harness."
- Keeping the coordinates stable means zero disruption to consumers or the published artifact.
- "HALO" reads positively (protection/oversight), keeps the word "Harness," and pairs naturally with APEX,
  EEIK, and Aether.

## Consequences

- README, `docs/index.html`, `CLAUDE.md`, and `project-manifest.yaml` present the HALO identity; the earlier
  "brand-neutral" language becomes "vendor-neutral."
- Peer repos gain a HALO cross-link. No code, package, or coordinate changes.
