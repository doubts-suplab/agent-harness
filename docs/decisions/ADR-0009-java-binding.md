# ADR-0009 — Java binding lives in the harness repo; aether-grid migrates onto it

- **Status:** Accepted
- **Date:** 2026-07-23

## Context

ADR-0002 committed to a language-neutral spec with a Python reference implementation and named "a Java
binding for aether-grid" as a follow-on. aether-grid already has a Java `Agent` SPI
(`execute(AgentInput) → AgentOutput`, decision enum `ALLOW/BLOCK/ALERT/DEFER/SUGGEST`) and an
`AgentOrchestrator`, but its confidence gate is **duplicated in three places** (`GovernanceAgent`,
`TemporalPredictionAgent`, and the `AgentOutput` backstop) with a hardcoded `0.8` literal and no named
constant, and it has **no tool registry** at all.

## Decision

Implement the Java binding as a **standalone Maven module inside the agent-harness repo** (`java/`,
`com.agentharness:agent-harness-java`), plain **Java 21**, framework-free (no Spring), brand-neutral — the
Java counterpart to the Python reference implementation, conformant to the same
[`harness-protocol.md`](../spec/harness-protocol.md) §9 checklist. It ships an `interop.LegacyAgentAdapter`
that wraps a grid-style agent so the harness's single `ConfidenceGate` decides enforcement.

aether-grid **consumes** this artifact (a later step): route its agents through the `Harness`, delete the
three duplicated gate checks, and gain the default-deny tool registry. Grid does not re-implement the
protocol; it depends on the binding — consistent with ADR-0001 (one shared runtime) and how apex-sdlc
consumes the Python package.

## Rationale

- Keeping both bindings in the harness repo mirrors where Python lives and keeps the protocol single-sourced.
- Plain Java 21 (no Spring) keeps the core framework-free (INV-5) and buildable standalone.
- The interop adapter proves the grid migration without a risky, build-gated change to grid in the same step.

## Consequences

- The harness repo now builds two ways: `pip install -e .` (Python) and `mvn test` in `java/` (Java, 22 tests).
- Grid's actual refactor (depend on the artifact, centralize the gate, add tool permissions) is a scoped
  follow-up touching a production module with JaCoCo/checkstyle gates — tracked in `docs/progress.md`.
- Where a published Maven artifact is needed, `mvn install` publishes `agent-harness-java` to the local repo
  until a real registry is set up.
