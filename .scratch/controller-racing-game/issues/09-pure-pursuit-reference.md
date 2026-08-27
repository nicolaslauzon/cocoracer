# 09: Pure-pursuit reference

**What to build:** The pure-pursuit baseline ported from the old experiment to the new controller API: centerline following with speed-scaled lookahead — the first controller to complete a lap-based race, and the strong reference every player tries to beat.

**Blocked by:** 08 (Race mode)

**Status:** ready-for-agent

- [x] Pure pursuit completes N laps on the stadium track (the first winning run of a lap-based race)
- [x] Head2head pure pursuit vs open-loop stub: pure pursuit finishes, stub DNFs
- [x] Pure-pursuit gains are parameters in the param file under its own baseline block

## Comments

- 2026-08-27: Done in `wt-09`. `PurePursuit` in `controllers/pure_pursuit.py`
  follows the centerline with a speed-scaled lookahead,
  `l_d = clip(slope * v + offset, min, max)` (the ax+b form), targets the
  centerline point one lookahead ahead, and commands
  `delta = atan(2 * L * y_local / chord^2)` with the chord to that target —
  the same law as the pre-package experiment, where targeting a point on
  the path (not a fixed point ahead) keeps the commanded arc through the
  target, so corners are tracked rather than cut.
  - The loader (`cocoracer/controller.py`) now passes the param file's
    `baselines` mapping to any controller class whose `__init__` declares a
    `baselines` parameter; `TrackInfo` carries the track centerline.
  - Gains: the block's original values (offset 1.0, max lookahead 15.0)
    were tuned for a large course; on the 24.6 m stadium a 7 m lookahead
    wraps past both corners and the run crashes every time. Retuned to
    slope 0.10, offset 0.6, min 0.5, max 2.5 (lookahead ~2.1 m at speed),
    target speed 15.0 unchanged: 3 laps finished clean, best lap ~1.6 s.
  - Tests: `tests/test_pure_pursuit.py` (loader baselines injection,
    TrackInfo centerline, 3-lap clean time trial, head2head vs the stub).
