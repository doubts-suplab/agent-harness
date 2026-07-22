# ADR-0004 — The tool registry is the runtime-enforced governance boundary

- **Status:** Accepted
- **Date:** 2026-07-22

## Context

AIEL treats the set of tools an agent can call as *the* governance boundary for agent capability: "A tool not
in the registry does not exist from the agent's perspective" and "This is enforced in the agent runtime, not
by convention" (`aether-iel/lifecycle/05-agent-engineering.md`). `governance-controls.md` §2.1 additionally
forbids wildcard permissions.

## Decision

Tool access is **default-deny**. Each agent declares an explicit allowlist of concrete tool names in its
Agent Contract. The harness authorizes every tool call against that allowlist **before any side effect**.
A call to a tool not in the allowlist is **refused** and logged as a **security event** — never silenced.
**Wildcards are forbidden**; allowlists enumerate concrete names. Each registry entry records name,
description, JSON-Schema parameters, and side-effect class (`none|read|write|external`).

## Rationale

- Runtime enforcement (not convention) is the only way the boundary actually holds.
- Explicit allowlists make the blast radius of any agent auditable and bounded.
- Side-effect class lets the harness decide when a call is subject to gate checks.

## Consequences

- A **supervisor** agent (ADR-0007) holds an **empty** allowlist — it coordinates, it does not act.
- Tool definition/call shapes reuse the apex-sdlc `integrations/llm/base.py` types so adapters map 1:1.
- Authorization failures are security-classified audit events by construction.
