# HALO — Python API reference

Generated reference for the **Python binding** of the HALO harness protocol (`agent_harness`). For the
project overview, the normative protocol, and the decision records, start at the
[repository root](https://github.com/doubts-suplab/agent-harness).

- **Protocol (normative):** [`docs/spec/harness-protocol.md`](https://github.com/doubts-suplab/agent-harness/blob/main/docs/spec/harness-protocol.md)
- **Overview & comparison:** [root README](https://github.com/doubts-suplab/agent-harness#readme)
- **Progress / roadmap:** [`docs/progress.md`](https://github.com/doubts-suplab/agent-harness/blob/main/docs/progress.md)

## Quickstart

```python
from agent_harness import AgentInput, AuthorityLevel, Decision, DecisionAction, Harness


class RefundApprover:
    name = "refund-approver"
    authority_level = AuthorityLevel.BLOCK
    capabilities = frozenset({DecisionAction.ALLOW, DecisionAction.BLOCK})

    def run(self, request, tools):
        if request.context["amount"] > 1000:
            return Decision(DecisionAction.BLOCK, 0.99, "over policy limit")
        return Decision(DecisionAction.ALLOW, 0.75, "within policy")


out = Harness().invoke(RefundApprover(), AgentInput("acme", "u1", context={"amount": 5000}))
# out.decision.auto_enforced was decided by the harness gate — never by the agent
```

See the [API reference](api.md) for the full surface.
