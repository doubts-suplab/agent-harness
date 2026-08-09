# HALO — Python binding (`halo_agent_harness`)

The **Python reference implementation** of the HALO harness protocol (`agent-harness`). This is one
conforming binding of a language-neutral spec; the Java binding lives in
[`../java`](../java), and the normative protocol + decision records live at the repo root under
[`../../docs`](../../docs).

- **Spec (normative):** [`../../docs/spec/harness-protocol.md`](../../docs/spec/harness-protocol.md)
- **Project overview:** [root `README.md`](../../README.md)
- **Progress / roadmap:** [`../../docs/progress.md`](../../docs/progress.md) · [`../../docs/roadmap.md`](../../docs/roadmap.md)

## Install & run

```bash
python3 -m venv .venv && source .venv/bin/activate   # Python 3.11+
pip install -e ".[test]"        # library + test deps (run from this directory)

pytest                          # conformance + unit suite (maps to spec §9)
python examples/quickstart.py   # end-to-end demo
```

```python
from halo_agent_harness import AgentInput, Harness      # zero-config: in-memory adapters by default
out = Harness().invoke(my_agent, AgentInput("tenant", "user", context={...}))
# out.decision.auto_enforced was decided by the harness gate — never by the agent
```

The **core** (`core`, `ports`, `orchestration`) has no third-party dependencies. `contract` validation
and the test suite pull `jsonschema`/`pytest` via extras.

## Layout

- `core/` — envelope, authority/decision model, confidence gate, tool registry, side-effect policy, harness.
- `orchestration/` — Pipeline (§6.1), Fan-out (§6.2), Debate/Consensus (§6.4), Supervisor + Workers (§6.3).
- `ports/` — LLM + governance Protocols. `adapters/` — in-memory reference adapters + LLM stub.
- `contract.py` — loads/validates Agent Contracts against the schema.
- `tests/` — conformance suite mapping 1:1 to spec §9, plus unit + framework-free tests.

License: AGPL-3.0. See [root `LICENSE`](../../LICENSE).
