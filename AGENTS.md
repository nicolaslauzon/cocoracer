## Coding style

Conventions are in `docs/coding-style.md` — read it before writing code.
Always run all four checks before committing:

```bash
ruff format .
ruff check .
mypy cocoracer tests
pytest -m "not slow"
```

## Running & verifying

Verify a controller by running it headless:

```bash
cocoracer time-trial --controller controllers/starter.py --no-web
```

`--params FILE` is a top-level flag that precedes the subcommand. In a git worktree there is no `.venv`, and the `cocoracer` script points at the main checkout, so run `.venv/bin/python -m cocoracer.cli ...` from the worktree root to test the branch's code. Full usage: `README.md`.

## Testing

The test suite has two tiers:

- **Fast** (~30s): unit + integration tests. Covers parsers, geometry, config, collision math, sensor ray-casting, protocol serialization, state machines, and engine seams. Run on every change.
- **Slow** (~9.5min): full-race E2E tests. Covers baseline controller completion, engine correctness under race conditions, CLI end-to-end, and performance budgets. Run when touching engine, vehicle, collision, or baseline controller code.

The test map at `tests/MAP.md` lists every test that takes >20s, with the source files it exercises. Consult it to decide which tests to run.

Before committing:

```bash
ruff format .
ruff check .
mypy cocoracer tests
pytest -m "not slow"  # fast suite — always
pytest -m slow        # slow suite — when touching engine/baselines
pytest --durations=0 -v  # regenerate timing data if tests change
```

## Agent skills

### Issue tracker
Issues and specs are local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`. Multi-session features keep running state in `.scratch/<feature-slug>/PROGRESS.md` — update it whenever a branch merges.

### Triage labels
Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in issue files. See `docs/agents/triage-labels.md`.

### Domain docs
Single-context: `CONTEXT.md` at repo root + ADRs in `docs/adr/`. See `docs/agents/domain.md`.
