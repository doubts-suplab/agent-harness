# ADR-0001 — The harness is a standalone, brand-neutral repository

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Project owner; harness architecture increment

## Context

The Aether/EEIK ecosystem has three layers relevant to running agents: a methodology/spec layer
(`aether-iel`, doc-only by its own decision D-001), a bootstrapping/config layer (`eeik-bootstrap`,
explicitly "not a runnable application"), and product runtimes (`apex-sdlc/platform`, `aether-grid`,
`aether-core`) that each **re-implement** agent execution. There is no shared, generic agent runtime;
the same shape (typed envelope → confidence gate → tool registry → orchestration → audit) is rebuilt per
product.

## Decision

The agent harness lives in its **own repository** (`doubts-suplab/agent-harness`), separate from the
methodology repo, the bootstrap repo, and any single product. It is **brand-neutral**: it depends on no
Aether product and imports no product internals. Products consume it; it consumes nothing from them.

## Rationale

- It is a **runtime** — it does not belong in `aether-iel` (no code) or `eeik-bootstrap` (not runnable).
- Placing it inside one product (e.g. apex) would couple a "generic" runtime to that product's stack.
- A neutral home lets apex-sdlc, aether-grid, and future consumers depend on one implementation instead of
  maintaining divergent copies.

## Consequences

- A new repo to maintain, with its own CI, versioning, and docs.
- Consumers integrate via a dependency + adapters, not a fork.
- Relationship to Aether is **through AIEL's contracts**, not through branding or code coupling.

## Alternatives considered

- **Inside `apex-sdlc/platform`** — fastest to a demo, but couples the harness to Python/FastAPI/Celery.
- **`eeik-bootstrap` capability pack only** — most bootstrappable, but no reference runtime to run/test.
  (Retained as a *complement*, not a substitute — see ADR-0008.)
