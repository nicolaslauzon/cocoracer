# pgm-racetracks — progress

Updated 2026-08-29. Master at `647ef43`, 241 tests passing.

## Done (merged to master)

- 01, 02, 03, 04, 08, 09, 10, 15 — track model, real-scale vehicle, PGM parse and mask, engine start gate, live start queue, protocol rework, gains→parameters
- 11, 12, 13, 14 — web view: road fill, true-scale car rectangles, fading trails + crash X, Start button (merge `c15f4d6`)
- 05 — centerline file: parse, scale, wall derivation, mask consistency (`cocoracer/maptrack.py`)
- 18 — hardcoded F1 zigzag start grid; `grid_spacing` removed from config and params

## Remaining

Chain, in order: **06 → 07 → 16 → 17**.

## Resume

1. Dispatch the ticket 06 agent in `/tmp/opencode/wt-pgm-06` (branch `pgm-06`, at master). If the directory is gone (it lives in /tmp): `git worktree add /tmp/opencode/wt-pgm-06 pgm-06 && git -C /tmp/opencode/wt-pgm-06 merge --ff-only master`. The brief is the ticket file plus the spec's "Start/finish", "Direction", and "Scale and grid" bullets.
2. When it returns: run the four checks, merge the branch into master, tick the ticket's boxes, commit the tick-off.
3. Repeat for 07, then 16, then 17.
Tooling: worktrees have no `.venv` — run `/home/nilau28/cocoracer/.venv/bin/python -m ruff format .`, `-m ruff check .`, `-m mypy cocoracer tests`, `-m pytest` from the worktree root. Full pytest is ~12 min; that dominates the chain's wall time.

## Map data notes

- `maps/<name>.{csv,yaml,pgm}` are canonical; the `-gimp` variants are display-only, ignored by the builder.
- Start pixels (image pixels, row 0 top) live in the ticket 07 text; all three verified on the centerline.

## Open question for the player

- Crash Xs land at the car's reported position on the crash tick — after the centerline reset — not at the wall contact point. The protocol carries no crash position. If the player wants the true contact point: the engine records it and the dynamic message gains one field.
