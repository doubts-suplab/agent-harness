# ADR-0005 — Ports & adapters: the core is framework-free; LLM/memory/audit/HITL are pluggable

- **Status:** Accepted
- **Date:** 2026-07-22

## Context

The harness must run across a polyglot, multi-store ecosystem (Anthropic/Groq/Ollama LLMs; pgvector memory;
Postgres audit; a review queue; OpenTelemetry). AIEL Phase 6 mandates hexagonal architecture: "No domain
dependency on infrastructure." apex-sdlc already ships a provider-agnostic LLM abstraction
(`apex-sdlc/platform/backend/app/integrations/llm/base.py`: `Message`/`ToolDefinition`/`ToolCall`/
`CompletionResult`/`LLMProvider` Protocol).

## Decision

The harness core is **framework-free** and expresses all I/O through **ports** (interfaces): `LlmPort`,
`ToolRegistryPort`, `PolicyPort`, `AuditPort`, `HumanReviewPort`, `ObservabilityPort`, `MemoryPort`,
`KillSwitchPort`. Concrete **adapters** are supplied at the edge and depend on the core — never the reverse.
`LlmPort` adopts the apex `LLMProvider` shape verbatim so existing adapters plug straight in.

## Rationale

- Keeps the safety-critical core (gate, registry, envelope) small, testable, and dependency-free.
- Lets each product supply its own LLM/memory/audit stack without touching the core.
- Reuses a proven provider abstraction instead of inventing a new one.

## Consequences

- Ports are part of the normative protocol (§7); adapters are not.
- A conformant implementation MUST keep the dependency direction adapters → core (checklist §9, INV-5).
- Memory access is always scoped by `tenantId` (+ collection/team where applicable) at the port boundary.
