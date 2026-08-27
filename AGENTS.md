## Coding style

Conventions are in `docs/coding-style.md` — read it before writing code.
Always run all four checks before committing:

```bash
ruff format .
ruff check .
mypy cocoracer tests
pytest
```

## Agent skills

### Issue tracker
Issues and specs are local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels
Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in issue files. See `docs/agents/triage-labels.md`.

### Domain docs
Single-context: `CONTEXT.md` at repo root + ADRs in `docs/adr/`. See `docs/agents/domain.md`.
