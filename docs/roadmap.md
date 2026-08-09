# HALO Roadmap

> Forward-looking plan for the HALO agent runtime (`agent-harness`). Increment-by-increment, in
> priority order. Companion to [`progress.md`](progress.md), which records what has shipped.
>
> **Status snapshot:** Increment 0 (spec) ✅ · Increment 1 (Python reference) ✅ · Increment 2
> (consumers: apex-sdlc, Java binding, aether-grid) 🚧 · **Increment 3 (protocol completeness:
> orchestration + side-effect gating) ✅** — delivered in both languages (see
> [`progress.md`](progress.md)). Increments 4–7 below are **planned, not started**.

---

## How to read this

Each item carries a **feasibility** and a **priority**.

| Feasibility | Meaning |
|---|---|
| **S** — Small | Docs, or a bounded change with a clear shape; low risk. |
| **M** — Moderate | A focused feature needing one design decision + tests. |
| **L** — Large | New language binding, distributed mechanism, or research-shaped work. |
| **⧗ External** | Blocked on credentials/accounts/infra outside the repo (flagged, not estimated). |

Priorities **P1–P5** follow the review's suggested order: (1) protocol completeness, (2) production
usefulness, (3) adoption, (4) test hardening + consumer migration, (5) cross-language + formal
conformance. Cross-cutting polish is interleaved.

**Invariant that governs every item below:** no change may create a path that bypasses the
confidence gate or the tool registry. `confidence_gate_bypass_total` stays permanently 0; new
orchestration, adapters, and side-effect gating all route through `Harness.invoke`.

**Licensing:** unchanged — AGPL-3.0 across the repo. The only license-related work here is
*documenting* its implications more prominently (Increment 5), not relicensing.

---

## Increment 3 — Protocol completeness (P1) ✅ Delivered

> **Delivered** in both Python and Java: Pipeline (§6.1), Fan-out (§6.2), Debate/Consensus (§6.4), a
> real Supervisor+Workers planning turn (§6.3), and side-effect gating (T-5, §5.3, ADR-0011). Spec +
> §9 conformance extended. See [`progress.md`](progress.md#increment-3--protocol-completeness--in-progress).

Close the gap between the normative spec (`docs/spec/harness-protocol.md`, ADR-0007) and the runtime.

| Deliverable | Feasibility | Notes |
|---|---|---|
| **Pipeline** orchestration (sequential stages, output→input) — Python + Java | **M** | Spec'd; each stage still goes through the gate/registry (O-1). Straightforward once the stage-passing contract is fixed. |
| **Parallel Fan-out** orchestration (independent workers, aggregated) — Python + Java | **M** | Needs a result-aggregation policy (collect / first-decisive); concurrency-safe accumulation of the bypass counter. |
| **Debate / Consensus** orchestration — Python + Java | **M–L** | Needs a consensus rule (majority / min-authority-wins / tie→DEFER). The safety floor: consensus can never raise authority above the strictest participant. |
| **Flesh out Supervisor+Workers**: actually invoke the supervisor agent to plan/delegate | **M** | Today it validates the empty allowlist and fans out; add a real planning turn. Keep the *supervisor-holds-no-tools* invariant (ADR-0007). |
| **Side-effect gating (T-5)**: harness consults `tool.side_effect` before execution | **M** | Registry already records `read/write/external/none`. Decide the policy: `write`/`external` require higher `autoEnforced` confidence and/or human review; log a security event on violation. Small design + wiring, high governance value. |
| Spec + ADR updates for the above; conformance tests extended 1:1 | **S** | Every new pattern adds a conformance case mapping to spec §9. |

**Exit:** all four orchestration patterns implemented in both languages with the O-1 invariant proven
by tests; side-effect class enforced before tool execution.

---

## Increment 4 — Production adapters & observability (P2)

Make the "pluggable ports" claim credible with real, optional adapters. Core stays framework-free;
adapters live behind the existing Protocol ports and are opt-in.

| Deliverable | Feasibility | Notes |
|---|---|---|
| **OpenTelemetry** `ObservabilityPort` exporter (traces + metrics) | **M** | Correlation IDs already propagate; map per-invocation spans (agent, action, confidence, duration, outcome) + OTLP export. Optional dependency. |
| **Durable `AuditPort`** adapter (append-only: JDBC / file / object store) | **M** | Mirror the append-only audit pattern already used across Aether (erasure/federation logs). PII-redacted. |
| **Real `HumanReviewPort`** queue adapter + **SLA enforcement/monitoring** | **M** | SLAs are defined in code but not enforced; add a deadline + a sweep/monitor hook (the Aether Flow escalation model is a reference, not a dependency). |
| **Production `LlmPort` providers** beyond the stub: one flexible **OpenAI-compatible HTTP adapter** + a preset registry (OpenAI, Groq, Ollama, Gemini's OpenAI-compat endpoint, Sarvam AI), plus a **native Anthropic** adapter (Messages API + `tool_use`). Adding a compatible provider is config, not code. | **M** | Async `httpx` (generic HTTP, the `llm` extra) — no provider SDKs; lazily imported, keys via env, offline-tested via an injected transport. Streaming deferred to a follow-up. |
| **Complete `MemoryPort` + `PolicyPort`** reference adapters (currently underdeveloped) | **M** | Bring them to parity with the other ports; add in-memory + one durable reference each. |
| **Richer redaction** (beyond basic patterns) + structured logging fields | **M** | Pluggable redaction strategy; document the default patterns and their limits. |
| **Cross-process kill-switch propagation** (`KillSwitchPort` durable/shared adapter) | **M–L** | Today the kill switch is in-process; add a shared-signal adapter (file/DB/Redis) so a trip propagates. Distributed correctness is the hard part. |
| **Metrics + a sample dashboard** (Prometheus/OTel + Grafana JSON) | **M** | Ships the bypass counter, routing rate, human-review latency as first-class metrics. |

**Exit:** a deployment can wire real telemetry, durable audit, a real review queue, and a real LLM
provider without touching the core; kill-switch trips propagate across processes.

---

## Increment 5 — Adoption: packaging, examples, standalone docs (P3)

Lower the barrier for someone outside the Aether family to evaluate and adopt HALO.

| Deliverable | Feasibility | Notes |
|---|---|---|
| **Standalone README section**: the problem HALO solves for a non-Aether user, a minimal non-ecosystem example, and a comparison table vs. common agent frameworks/runtimes | **S** | Highest adoption-per-effort. De-jargon the top of the README (AIEL/APEX/EEIK/Aether pushed below the fold). |
| **More examples** (Python): multi-agent orchestration, contract load + validate, failure modes; **Java** equivalents | **S–M** | Today there is only `quickstart.py`. |
| **Public API docs**: MkDocs/Sphinx (Python) + Javadoc (Java), published as static site | **M** | `docs/index.html` is currently minimal; generate real reference docs. |
| **CHANGELOG.md** + **stability & deprecation policy** | **S** | Publish semver guarantees once the protocol solidifies (still 0.x today — say so explicitly). |
| **Prominent AGPL-3.0 implications callout** for proprietary consumers | **S** | License **unchanged**; add a clear "what AGPL means for you" note in README + a `LICENSING.md`. |
| **Agent Contract validation CLI** + more worked contract examples | **S–M** | `halo validate-contract path.json` against the JSON Schema + binding rule; broadens the schema's usefulness. |
| **PyPI + Maven Central** publication with semantic versioning | **⧗ External** | Needs registry accounts + signing secrets (org-level). Wire the workflows now; the actual publish is gated on credentials. |

**Exit:** a newcomer can `pip install`/Maven-depend, read standalone docs, run several examples, and
understand the license implications — without Aether context.

---

## Increment 6 — Test hardening & consumer migration (P4)

Prove the safety guarantees under stress, and finish the in-flight consumer work.

| Deliverable | Feasibility | Notes |
|---|---|---|
| **Concurrency / race tests** around the gate and registry | **M** | Prove "never fails open" under parallel invocation; assert the bypass counter stays 0 under load. |
| **Property-based / fuzz tests** of the envelope + binding rule (Hypothesis / jqwik) | **M** | Generative coverage of the two-axis authority/decision model and the binding rule. |
| **Failure-injection / E2E** with realistic mocked LLM + tool side effects | **M** | Partial-failure and timeout paths must degrade to safe defaults with lowered confidence + `autoEnforced=false`. |
| **Cross-language interop tests** beyond `LegacyAgentAdapter` | **M** | Same contract → same decision in Python and Java. |
| **Mutation testing** (mutmut / PIT) targeting the gate invariant | **M** | Stronger assurance that "bypass counter == 0" is actually enforced, not just asserted. |
| **CI upgrades**: coverage reporting, Python/Java version matrix, conformance badge | **S–M** | Extends the existing Python+Java CI. |
| **Finish the remaining 6 aether-grid agent migrations** + document the migration path | **M** | Cross-repo (aether-grid); closes Increment 2's incremental-migration note. |
| **Close the eeik-bootstrap divergent-manifest-schema item** | **M** | Cross-repo (eeik-bootstrap); the last open Increment-2 checkbox. |

**Exit:** safety invariants are proven under concurrency/partial failure; all grid agents run on the
harness; the eeik manifest reconciliation is closed.

---

## Increment 7 — Cross-language surface & formal conformance (P5)

Broaden reach and let external implementations self-certify.

| Deliverable | Feasibility | Notes |
|---|---|---|
| **TypeScript binding** (thin) — envelope, gate, registry, one orchestration pattern | **L** | The protocol is language-neutral by design; a third binding validates that claim and broadens adoption. |
| **Formal external conformance suite** runnable by any implementation | **L** | Package spec §9 as a language-agnostic, runnable suite (fixtures + expected decisions) so a new binding can prove conformance. |

**Exit:** a third language binding exists and an external team can certify their own implementation
against the spec.

---

## Cross-cutting — design/API polish & community (interleaved, mostly P3–P4)

| Deliverable | Feasibility | Notes |
|---|---|---|
| **Stricter public surface** so agents cannot accidentally influence enforcement | **S–M** | Extend the existing defensive resets (e.g. forcing `auto_enforced=false`); make enforcement fields read-only to agents. |
| **Configurable decision hierarchy with a safety floor** (or document why fixed) | **M** | Allow reordering above the floor; the floor (confidence < 0.8 → never auto-enforce) stays immovable. |
| **CONTRIBUTING.md, issue/PR templates, public roadmap** (this file) | **S** | Community on-ramp; 1★/0 forks today. |
| **Non-Aether usage examples** + comparison table | **S** | Positioning for outsiders. |
| **Dual-naming consistency** (HALO ⇄ `agent-harness`) everywhere | **S** | ADR-0010 already sets the convention; audit README/docs/package metadata for consistency. |
| **Rebrand to `halo-agent-harness` / `com.suplab.agentharness`** ✅ Done | **M** | [ADR-0013](decisions/ADR-0013-halo-rebrand.md) (supersedes ADR-0010). Full rename — coordinates **and** code namespaces: PyPI `halo-agent-harness`, import `halo_agent_harness`, Maven `com.suplab.agentharness:halo-agent-harness`, package `com.suplab.agentharness.*`. Breaking for consumers (apex-sdlc, aether-grid, eeik) — they migrate in their own repos. Repo name unchanged. |

---

## Feedback → increment traceability

| Review section | Tracked in |
|---|---|
| 1. Protocol completeness (orchestration, side-effect gating, supervisor) | Increment 3 |
| 1. Ports underdeveloped (Memory/Policy) + real adapters | Increment 4 |
| 2. Observability, audit, SLA, kill-switch, multi-tenant | Increment 4 (+ Increment 6 tests) |
| 3. Docs, onboarding, standalone framing, API docs, AGPL callout | Increment 5 |
| 4. Testing & quality (concurrency, fuzz, mutation, CI) | Increment 6 |
| 5. Packaging/distribution, TS binding, conformance suite, open items | Increment 5 (packaging) · Increment 6 (open items) · Increment 7 (TS + conformance) |
| 6. Design & API polish | Cross-cutting |
| 7. Visibility & community | Cross-cutting + Increment 5 |

> This roadmap is a living plan. Items move to [`progress.md`](progress.md) as they ship. No delivery
> is claimed here — Increments 3–7 are **not started**.
