# Coding style

Conventions for the cocoracer codebase. Machine-checkable rules are enforced by
[ruff](https://docs.astral.sh/ruff/) and [mypy](https://mypy.readthedocs.io/)
(config lives in `pyproject.toml`); this doc covers the judgment calls they
can't check.

## Tooling

Install dev tools with `pip install -e ".[dev]"`, then run all four checks
before committing:

```bash
ruff format .
ruff check .
mypy cocoracer tests
pytest
```

## Formatting

- `ruff format` is the only formatter; 88-character lines.
- Imports are sorted by ruff; never order them by hand.
- Keep syntax compatible with Python 3.10 (ruff `target-version` is `py310`).

## Type hints

- Every function signature is fully annotated — arguments and return type —
  including in tests and private helpers.
- mypy runs with `disallow_untyped_defs`; a non-clean `mypy cocoracer tests`
  run blocks the commit.

## Naming

- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Module-level constants: `UPPER_SNAKE`
- Private helpers: leading underscore (e.g. `_build_track`)
- Test files: `test_<module>.py`; test functions: `test_<behavior>`

## Module layout

- `cocoracer/` — the package: `cli.py` (entry point), `config.py`
  (YAML → dataclasses), `track.py` (track geometry: centerline, Frenet,
  occupancy grid, wall queries), `sensor.py` (full-circle fleet laser scan:
  walls plus racing vehicles' collision circles), `collision.py` (batched
  crash detection: walls first, then racing pairs), `vehicle.py` (per-vehicle
  record: pose, motion, race state, and the centerline consequence: anchor,
  per-tick lap recording, crash), `controller.py`
  (player controller API + file loader), `dynamics.py` (batched JAX vehicle
  model), `race_state.py` (per-vehicle race record: status, crash/pause/ghost
  timers, laps, DNF), `lap_tracker.py` (lap-counting machine:
  checkpoint-gated lap booking), `engine.py` (headless race loop).
- `controllers/` — player controller files (one class per file); this is
  the one folder that lives beside the package, since players edit it.
- `params/` — YAML track/vehicle/sim parameters.
- `tests/` — mirrors the package, one test file per module.
- New top-level concepts go inside `cocoracer/`; don't add files at the repo root.

## Docstrings

- Google style, public API only (names exported from `cocoracer/__init__.py`
  plus functions users call directly).
- One-line summary when self-evident; `Args:`/`Returns:` sections only when
  they add information beyond the type hints.
- Private `_`-prefixed helpers get no docstring unless the *why* is non-obvious.

## Tests

- pytest; one file per module (`tests/test_track.py` ↔ `cocoracer/track.py`).
- Shared session-scoped fixtures live in `tests/conftest.py`.
- Test behavior through the public API where possible; cover the error paths
  that raise `ConfigError` / `TrackError`.
