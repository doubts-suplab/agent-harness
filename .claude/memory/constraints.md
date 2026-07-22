# Hard Constraints — agent-harness

From the protocol (`docs/spec/harness-protocol.md`). These never bend.

- Confidence gate is in the core, runs on every invocation, and **cannot be disabled** (no flag/env/API).
- `autoEnforced` is set by the harness, **never** by an agent.
- Tool access is **default-deny**; allowlists are explicit; **no wildcards**; supervisors hold no tools.
- No runtime authority **self-escalation**.
- Audit is **append-only** and **PII-redacted**; BLOCK/ALERT carry a human-readable explanation.
- Every failure resolves to a **safe** decision (lowered confidence, `autoEnforced=false`) — never fail open.
- `confidence_gate_bypass_total` is emitted and MUST remain `0`.
- The **core is framework-free**: adapters depend on the core, never the reverse.
- The **spec is normative**: code conforms to it, not vice versa.
