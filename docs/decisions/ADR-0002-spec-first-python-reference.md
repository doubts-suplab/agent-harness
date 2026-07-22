# ADR-0002 — Language-neutral protocol spec, with a Python reference implementation

- **Status:** Accepted
- **Date:** 2026-07-22

## Context

The ecosystem is polyglot: the aether products are Java 21 / Spring Boot, while apex-sdlc (the active
consumer on this branch and the one that already specifies a harness) is Python 3.12 / FastAPI. AIEL's
Phase 6 standards are written around a specific Java/Spring/pgvector stack, but the *methodology* it encodes
(contracts → runtime gate → tool registry → observability) is stack-agnostic.

## Decision

Define the harness as a **language-neutral protocol specification** first
([`harness-protocol.md`](../spec/harness-protocol.md) + [`agent-contract.schema.json`](../spec/agent-contract.schema.json)).
The first **reference implementation** targets **Python 3.11+** (Increment 1; developed on 3.12, floor set to
3.11). Other bindings (a Java binding for aether-grid) follow the same protocol.

> **Amendment (Increment 2):** the `requires-python` floor was lowered from 3.12 to **3.11** so the first
> real consumer, apex-sdlc (Python 3.11), can depend on the harness. The core uses no 3.12-only syntax and
> the full suite passes on both 3.11 and 3.12.

## Rationale

- A neutral spec lets every product conform without inheriting one language's runtime.
- Python-first gives the fastest path to a real, end-to-end consumer (apex-sdlc) that proves the protocol.
- The spec is the contract of record; implementations are conformant or not against it (§9 checklist).

## Consequences

- Increment 0 ships **no runtime code** — only the spec, schema, and this decision set.
- Conformance is testable independently of language via the §9 checklist.
- Divergence risk between bindings is controlled by the single normative spec.
