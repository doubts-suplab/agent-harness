# /adr — Architecture Decision Record

Scaffold a new ADR in `docs/decisions/` for this repo.

## Usage
```
/adr "decision title"
```

## Execution
1. Determine the next number by scanning `docs/decisions/ADR-*.md`.
2. Create `docs/decisions/ADR-{NNNN}-{kebab-case-title}.md` using the section layout of the existing ADRs
   (Status, Date, Context, Decision, Rationale, Consequences, Alternatives considered).
3. If the decision changes the protocol, also update `docs/spec/harness-protocol.md` and note it in the ADR.
4. Record a one-line summary in `.claude/memory/decisions.md`.
5. Keep `README.md` / `docs/index.html` / `docs/progress.md` in sync if scope changed (Documentation Sync Rule).
