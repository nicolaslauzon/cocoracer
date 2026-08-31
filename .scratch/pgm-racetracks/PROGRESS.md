# pgm-racetracks — progress

Updated 2026-08-29. Master at `dea1cb8`, fast suite 247 passing + 18 slow (player-verified).

## Done (merged to master)

- 01, 02, 03, 04, 08, 09, 10, 15 — track model, real-scale vehicle, PGM parse and mask, engine start gate, live start queue, protocol rework, gains→parameters
- 11, 12, 13, 14 — web view: road fill, true-scale car rectangles, fading trails + crash X, Start button (merge `c15f4d6`)
- 05 — centerline file: parse, scale, wall derivation, mask consistency (`cocoracer/maptrack.py`)
- 18 — hardcoded F1 zigzag start grid; `grid_spacing` removed from config and params
- 06 — direction key, start-line re-fit, occupancy grid, `maps` config section, end-to-end map build
- 07 — three maps shipped, CLI-selectable; directions: right-interior ccw, icra-2023-short ccw, icra-2025 cw

## Remaining

None — **16** merged to master (`37b3055`/`fa8f29f`); **17** closed without implementation on the player's decision (2026-08-31): the baselines will be fine-tuned by hand, so the half-lap bar, the verification script, and the extra CI smoke are dropped. See the ticket file for the annotated acceptance list.

## Resume

1. Dispatch the ticket 16 agent in `/tmp/opencode/wt-pgm-16` (branch `pgm-16`, at master). If the directory is gone (it lives in /tmp): `git worktree add /tmp/opencode/wt-pgm-16 pgm-16 && git -C /tmp/opencode/wt-pgm-16 merge --ff-only master`. The brief is the ticket file plus the spec's "F1 removal" and "Stadium" bullets and the ADR notes in "Further Notes".
2. When it returns: run the four checks, merge the branch into master, tick the ticket's boxes, commit the tick-off, push.
3. Then dispatch 17 (baseline re-tune) the same way.
Tooling: worktrees have no `.venv` — run `/home/nilau28/cocoracer/.venv/bin/python -m ruff format .`, `-m ruff check .`, `-m mypy cocoracer tests` from the worktree root. Tests are two-tier: `pytest -m "not slow"` (~35 s) for the dev loop, `pytest -m slow` (~10 min) when touching engine/baselines. Slow-test map: `tests/MAP.md`.

## Map data notes

- `maps/<name>.{csv,yaml,pgm}` are canonical; the `-gimp` variants are display-only, ignored by the builder.
- Start pixels (image pixels, row 0 top) live in the ticket 07 text; all three verified on the centerline.

## Open question for the player

- Crash Xs land at the car's reported position on the crash tick — after the centerline reset — not at the wall contact point. The protocol carries no crash position. If the player wants the true contact point: the engine records it and the dynamic message gains one field.
