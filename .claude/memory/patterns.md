# Approved Patterns — agent-harness

- **Hexagonal / ports-and-adapters.** Core defines port interfaces; adapters implement them at the edge.
- **Reuse the apex LLM port shape** (`Message`/`ToolDefinition`/`ToolCall`/`CompletionResult`/`LLMProvider`)
  from `apex-sdlc/platform/backend/app/integrations/llm/base.py` — do not invent a new LLM abstraction.
- **Supervisor + Workers** is the default multi-step orchestration; supervisor holds no tools.
- **Two-axis decision model**: static `authorityLevel` + dynamic `capabilities` (DecisionActions), bound by §3.3.
- **Safe failure defaults** table (spec §8) applies whenever an Agent Contract is silent on a failure mode.
