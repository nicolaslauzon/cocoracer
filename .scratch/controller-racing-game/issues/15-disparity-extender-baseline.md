# 15: Disparity-extender baseline

**What to build:** The disparity-extender reactive baseline, following F1TENTH Lecture 5 semantics (redirected from the original "follow the gap"): laser-only, no centerline. Over the front sector (±90°), extend each range edge (adjacent beams differing by more than a threshold) across the car's width so the car does not aim a gap it cannot physically fit through; steer toward the farthest extended beam with a P/D law on its angle; speed comes from the distance to that target (full speed when far, a flat brake zone when close, linear in between), capped by the friction-limited speed for the commanded steering angle. Every gain is a parameter in the param file under its own baseline block.

**Blocked by:** 09 (Pure-pursuit reference)

**Status:** ready-for-agent

- [x] Disparity extender completes N laps on the stadium track (headless run)
- [x] All gains (car width, wheelbase, P/D gains, speed curve, friction, disparity threshold) are parameters in the param file
- [x] Speed is limited by distance to the target and scales down with steering angle (friction cap)
- [x] Head2head disparity extender vs pure pursuit runs end-to-end with a valid results table

## Comments

- 2026-08-28: Done in `wt-15`. Replaced the originally planned follow-the-gap
  (Lecture 5) with the Disparity Extender from the same lecture, per user
  direction, ported from a working C++ ROS reference.
  `DisparityExtender` in `controllers/disparity_extender.py`:
  - Front sector ±90°; an edge is a pair of adjacent beams whose ranges differ
    by at least `disparity_threshold`; each edge's nearer side is propagated
    outward over the arc the car's width subtends at that range (clamped,
    never pushed farther) so the car does not aim a gap it cannot fit through.
    The target is the farthest extended beam (ties → the middle). Steering is
    a P/D law on the target angle; speed is a piecewise function of the
    distance to the target, then capped by the friction-limited speed for the
    commanded steering angle (sigmoid-blended between the two).
  - Tuning note: on the 1 m-wide stadium the car is always within a car-width
    of a wall, so a low threshold smears the near wall across the forward
    field and the car crawls (best lap 11.6 s at threshold 0.2), while no
    extension at all (threshold ~100) clips the walls and DNFs after 5
    crashes. Threshold 2.0 keeps the extension acting as a crude wall margin
    without collapsing the far field. Final: kp 0.6, kd 3.0,
    full_speed_distance 5.0, min_speed 1.5, max_speed 18.0, friction 0.52,
    disparity_threshold 2.0 → 3 laps finished clean, best lap 4.15 s.
  - Tests: `tests/test_disparity_extender.py` (loader baselines injection,
    empty-scan hold behavior, missing-gain-key rejection, 3-lap clean time
    trial, head2head vs pure pursuit producing a valid results table with pure
    pursuit winning).
