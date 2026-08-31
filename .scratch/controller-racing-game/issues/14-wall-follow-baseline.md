# 14: Wall-follow baseline

**What to build:** The wall-follow baseline, following F1TENTH Lab 3 semantics: scan a forward sector, hold a target lateral distance from the chosen wall via a P/D controller on the heading error to an offset target point, with speed = v_ref × (1 − k·|steering|) clamped. Every gain, offset, sector angle, and speed factor is a parameter in the param file under its own baseline block, so aggressiveness is tunable without code changes.

**Blocked by:** 09 (Pure-pursuit reference)

**Status:** done

- [x] Wall follow completes N laps on the stadium track (headless run)
- [x] All gains (target wall distance, P and D gains, v_ref, steering-speed factor, sector angles) are parameters in the param file and changing them changes behavior
- [x] Speed scales down with steering angle (observable in run telemetry/results)
- [x] Head2head wall follow vs pure pursuit runs end-to-end with a valid results table

## Comments

- 2026-08-28: Done in `wt-14`. The forward-sector nearest-hit aim-point variant
  (spec form, no two-beam trig) is what shipped: on the 1 m stadium the car is
  always within a car-width of a wall, so the "nearest wall" is ambiguous near the
  centerline and a stiff P law (the draft's kp=1.0) saturates at ±max steer and
  weaves into a wall — a limit cycle that DNF'd at 5 crashes in ~6 s. Softer P
  (kp=0.45), real damping (kd=2.0), and a low reference speed (v_ref=4.0) break
  the cycle: the car holds 0.3 m off the wall and carries 3 clean laps
  (best 6.77 s, 0 crashes), deterministic across 3 runs. Speed visibly scales
  down with |steer| (v_ref·(1−0.5·|steer|)), and the head2head vs pure-pursuit
  runs end-to-end with a valid table (pure-pursuit wins in 1.6 s/lap; the
  ~4x-slower wall-follower gets lapped and DNFs on max crashes, which the engine
  reports correctly). All six gains live in `baselines.wall_follow`.
