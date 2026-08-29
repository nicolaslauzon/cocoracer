## Coding style

Conventions are in `docs/coding-style.md` — read it before writing code.
Always run all four checks before committing:

```bash
ruff format .
ruff check .
mypy cocoracer tests
pytest
```

## Running & verifying

Verify a controller by running it headless:

```bash
cocoracer time-trial --controller controllers/starter.py --no-web
```

`--params FILE` is a top-level flag that precedes the subcommand. In a git worktree there is no `.venv`, and the `cocoracer` script points at the main checkout, so run `.venv/bin/python -m cocoracer.cli ...` from the worktree root to test the branch's code. Full usage: `README.md`.

## Agent skills

### Issue tracker
Issues and specs are local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`. Multi-session features keep running state in `.scratch/<feature-slug>/PROGRESS.md` — update it whenever a branch merges.

### Triage labels
Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in issue files. See `docs/agents/triage-labels.md`.

### Domain docs
Single-context: `CONTEXT.md` at repo root + ADRs in `docs/adr/`. See `docs/agents/domain.md`.
