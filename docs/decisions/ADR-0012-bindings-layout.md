# ADR-0012 — Language bindings live under `bindings/<lang>`

- **Status:** Accepted
- **Date:** 2026-08-08
- **Supersedes (layout only):** the repo-root placement described in
  [ADR-0002](ADR-0002-spec-first-python-reference.md) and [ADR-0009](ADR-0009-java-binding.md).

## Context

The harness protocol is language-neutral by design (ADR-0001, ADR-0002): the normative artifact is the
spec, and each implementation is a *conforming binding*. Yet the repository layout contradicted that
framing. The Python implementation sat at the repository root (`src/`, `tests/`, `pyproject.toml`,
`examples/`), while Java was tucked into a nested `java/` directory. That asymmetry read as "Python is
the project, Java is an add-on," and it left no clean home for the planned TypeScript binding
(roadmap Increment 7).

## Decision

Adopt a **`bindings/<lang>` layout**. Each language implementation is a self-contained peer:

```
docs/spec/        normative protocol + Agent Contract schema (canonical, language-neutral)
docs/decisions/   ADRs
bindings/python/  src/ tests/ examples/ pyproject.toml (+ a binding-local README)
bindings/java/    src/ pom.xml (+ README)
bindings/…        future bindings (e.g. typescript/) slot in identically
```

The spec, ADRs, root `README.md`, `CLAUDE.md`, and `project-manifest.yaml` stay at the root as the
shared, language-neutral source of truth. Package coordinates are unchanged: `agent-harness` (PyPI name),
`com.agentharness` (Maven group), `agent_harness` (Python import).

## Rationale

- The layout now *states* the architecture: no binding is privileged; all conform to one spec.
- A third (or fourth) binding is a new sibling directory, not a special case.
- Each binding keeps its own build metadata and README, which is also cleaner for independent
  PyPI / Maven publication (roadmap Increment 5).
- History is preserved: the move used `git mv`.

## Consequences

- **Build/test paths change.** Python: `cd bindings/python && pip install -e ".[test]" && pytest`.
  Java: `cd bindings/java && mvn test`. CI `working-directory` and the Java publish workflow are updated.
- `bindings/python/pyproject.toml` keeps its relative `src`/`tests` config (they moved with it) and points
  `readme` at a new binding-local `README.md` (setuptools cannot reference a file outside the project dir).
- The contract test resolves the repo root via `parents[3]` to reach the canonical `docs/spec/examples/`.
- Docs referencing `src/agent_harness/` or `java/` are updated to `bindings/python/…` / `bindings/java/…`.
- Historical ADRs (0002, 0009) are left intact as point-in-time records; this ADR records the relocation.
