# agent-harness — Java binding

The Java binding of the [harness protocol](../docs/spec/harness-protocol.md) — the counterpart to the
Python reference implementation. Plain **Java 21**, framework-free (no Spring), brand-neutral
(`com.agentharness`). Same normative behaviour, same §9 conformance checklist.

## Build & test

```bash
cd java
mvn test        # 21 tests: 19 conformance (ConformanceTest) + 2 interop (LegacyAgentAdapterTest)
```

## Shape

| Package | Contents |
|---|---|
| `com.agentharness.model` | `AgentInput`, `Decision`, `AgentOutput`, `AuthorityLevel`, `DecisionAction`, `Decisions` (binding rule + hierarchy), `FailureMode` |
| `com.agentharness` | `Agent`, `ToolInvoker`, `ConfidenceGate`, `ToolRegistry`, `Harness`, exceptions |
| `com.agentharness.ports` | `LlmPort`, `AuditPort`, `HumanReviewPort`, `ObservabilityPort`, `KillSwitchPort`, `MemoryPort` (DTOs nested) |
| `com.agentharness.adapters` | In-memory reference adapters + `Redaction` (PII) |
| `com.agentharness.orchestration` | `SupervisorWorkers` + `OrchestrationResult` |
| `com.agentharness.interop` | `LegacyAgentAdapter` — the aether-grid migration path |

```java
Harness harness = Harness.withInMemoryAdapters();
AgentOutput out = harness.invoke(agent, new AgentInput("tenant", "user", Map.of(), Map.of()));
// out.decision().autoEnforced() was decided by the harness gate — never by the agent
```

## aether-grid migration

Grid's `Agent` SPI (`execute(AgentInput) -> AgentOutput`) and decision enum map directly onto this binding.
Grid today duplicates the `confidence >= 0.8` gate in **three** places (`GovernanceAgent`,
`TemporalPredictionAgent`, and the `AgentOutput` backstop) with a hardcoded literal. `LegacyAgentAdapter`
shows the fix: a legacy agent emits only *action + confidence + rationale*, and the single
`ConfidenceGate` decides enforcement — one place, independently testable, impossible for an agent to
bypass. See `LegacyAgentAdapterTest` (mirrors grid's `GovernanceAgentTest` threshold cases). Grid also
gains a **tool registry** (net-new — grid has no tool concept today).

The next step is for `aether-grid` to depend on this artifact (`com.agentharness:agent-harness-java`) and
route its agents through the `Harness`, deleting the duplicated gate logic.
