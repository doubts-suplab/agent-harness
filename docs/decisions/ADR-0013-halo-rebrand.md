# ADR-0013 — Rebrand to `halo-agent-harness` / `com.suplab.agentharness`

- **Status:** Accepted
- **Date:** 2026-08-09
- **Supersedes:** [ADR-0010](ADR-0010-halo-brand.md) (the HALO-brand ⇄ neutral-coordinates convention).

## Context

ADR-0010 kept HALO as a *product identity* while the published/importable coordinates stayed neutral
(`agent-harness`, `com.agentharness`, `agent_harness`). In practice the split caused friction: the brand
and the artifacts a consumer actually types were different names, and the Maven group `com.agentharness`
was an unowned, unverifiable namespace for Central publishing. The maintainer decided to unify the brand
across **every** surface, including the code-level namespaces.

## Decision

Rebrand fully — coordinates **and** code namespaces:

| Surface | Before | After |
|---|---|---|
| PyPI distribution | `agent-harness` | `halo-agent-harness` |
| Python import package | `agent_harness` | `halo_agent_harness` |
| Console script | `halo` | `halo` (unchanged) |
| Maven groupId | `com.agentharness` | `com.suplab.agentharness` |
| Maven artifactId | `agent-harness-java` | `halo-agent-harness` |
| Java package | `com.agentharness.*` | `com.suplab.agentharness.*` |
| Git repo / dir | `agent-harness` | `agent-harness` (unchanged) |

The repository name, the spec, and the protocol semantics are unchanged. This is a naming change only —
no invariant, envelope, gate, registry, or port contract is altered.

## Consequences

- **Breaking for consumers.** apex-sdlc, aether-grid, and eeik import `agent_harness` /
  `com.agentharness.*` today; they must migrate to the new names. This was accepted explicitly, over the
  non-breaking "coordinates-only" alternative (keep the import/package names, change only what's
  published), which was considered and rejected in favour of full consistency.
- **Publishing.** The Maven Central namespace to verify becomes `com.suplab.agentharness`; the PyPI
  project and its Trusted Publisher use `halo-agent-harness`. See [`../publishing.md`](../publishing.md).
- **Cross-repo follow-up.** The consumer repos and any `eeik-bootstrap` capability-pack metadata that
  names the old coordinates need updating in their own repositories (out of scope for this repo's change).
- **One-time churn.** Directory moves use `git mv` to preserve history; imports and package declarations
  are updated mechanically. Protocol version stays `0.1.0`.
