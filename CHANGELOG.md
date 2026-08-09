# Changelog

All notable changes to **HALO** (`agent-harness`) are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning & stability policy

HALO is **`0.x`** — pre-1.0. Per SemVer, this means:

- **The protocol may still change.** The normative contract in
  [`docs/spec/harness-protocol.md`](docs/spec/harness-protocol.md) (the envelope, the two-axis
  authority/decision model, the confidence gate, the tool registry, the ports) is stabilising but **not
  yet frozen**. Minor `0.x` releases may introduce breaking changes; they will be called out under a
  **Changed** / **Removed** heading here.
- **The safety invariants will not weaken.** Across any version, the confidence gate stays centralized
  and non-disableable, `confidence_gate_bypass_total` stays `0`, tool access stays default-deny, and no
  change may create a path that fails open. These are guarantees, not features subject to deprecation.
- **Deprecations** get one minor release of overlap where practical: the old surface keeps working, is
  marked deprecated in code and noted under **Deprecated** here, and is removed no earlier than the next
  minor release.
- **1.0** will be cut once the protocol is frozen and a language-agnostic conformance suite exists
  (roadmap Increment 7). From 1.0, breaking protocol changes require a major version.

Both language bindings track the same protocol version. The Python package version is in
[`bindings/python/pyproject.toml`](bindings/python/pyproject.toml); the Java coordinates are in
[`bindings/java/pom.xml`](bindings/java/pom.xml).

---

## [Unreleased]

### Changed (BREAKING)

- **Rebranded to `halo-agent-harness` / `com.suplab.agentharness`** ([ADR-0013](docs/decisions/ADR-0013-halo-rebrand.md),
  supersedes ADR-0010). Full rename across coordinates **and** code namespaces:
  - PyPI distribution `agent-harness` → **`halo-agent-harness`**; Python import `agent_harness` → **`halo_agent_harness`**.
  - Maven `com.agentharness:agent-harness-java` → **`com.suplab.agentharness:halo-agent-harness`**; Java package `com.agentharness.*` → **`com.suplab.agentharness.*`**.
  - Consumers must update their imports/coordinates. The Git repository name, the spec, and the protocol semantics are unchanged; version stays `0.1.0`.

## [0.1.0] — Increments 0–4

Pre-release development. Grouped by increment (see [`docs/progress.md`](docs/progress.md) for detail).

### Added

- **Increment 0 — Specification.** Normative, language-neutral
  [harness protocol](docs/spec/harness-protocol.md); machine-readable
  [Agent Contract schema](docs/spec/agent-contract.schema.json); ADR-0001..0012.
- **Increment 1 — Python reference.** Framework-free core (envelope, two-axis authority/decision model,
  centralized confidence gate, default-deny tool registry, harness), Supervisor+Workers, ports as
  Protocols with in-memory reference adapters, and a contract loader.
- **Increment 2 — Java binding + first consumers.** `com.agentharness:agent-harness-java` (plain Java 21)
  with the same protocol and §9 conformance checklist; apex-sdlc runs all seven SDLC phase agents on the
  harness; aether-grid consumes the Java binding.
- **Increment 3 — Protocol completeness** (Python + Java). All four orchestration patterns — Pipeline
  (§6.1), Fan-out (§6.2), Debate/Consensus (§6.4), and Supervisor+Workers with a real, harness-governed
  planning turn (§6.3) — plus **side-effect gating** (T-5, §5.3, ADR-0011): `write`/`external` tool calls
  are gated on confidence before execution.
- **Increment 4 — Production adapters** (in progress). Human-review SLA monitoring + audited override
  endpoint (§7.4); durable append-only file `AuditPort` (§7.3); cross-process file kill switch (§7.6);
  in-memory + durable `MemoryPort` and an immutable rule-based `PolicyPort` (§7); pluggable
  `RedactionStrategy` (§7.3); optional OpenTelemetry `ObservabilityPort` exporter (§7.5); and production
  `LlmPort` providers — an OpenAI-compatible HTTP adapter with a provider preset registry (OpenAI, Groq,
  Ollama, Gemini, Sarvam AI) plus a native Anthropic adapter.

### Structure

- Adopted the `bindings/<lang>` repository layout (ADR-0012); the spec and ADRs live at the root as the
  shared, language-neutral source of truth.

[Unreleased]: https://github.com/doubts-suplab/agent-harness/compare/main...HEAD
[0.1.0]: https://github.com/doubts-suplab/agent-harness/commits/main
