# 02: Headless engine, dynamics & race rules

**What to build:** The complete headless race loop. A JAX kinematic bicycle model (batched over all vehicles in one jitted call, RK4 substeps, with acceleration/speed/steering-angle/steering-rate constraints) is stepped at 40 Hz. Per tick, in order: each racing controller is stepped with its state, commands are applied, dynamics integrate, wall collisions are checked against the occupancy grid with the vehicle footprint, crash handling runs, and laps are booked. A crash places the car at the nearest centerline pose (centerline heading, zero speed/steering), then a 0.5 s pause (zero outputs, controller not consulted), then a 1.5 s ghost phase. Lap counting is gated by the start/finish line plus a mid-track checkpoint. DNF fires on timeout or max crashes. Results carry per-vehicle finish order, total time, best/last lap, and DNF reason. The controller API ships: a base class (reset + per-tick step returning speed and steering), a loader that dynamically imports a player file and finds its single concrete controller class, and an open-loop stub in the controllers folder (constant forward speed — the honest player starting point). `time-trial --no-web` runs all of this headless.

**Blocked by:** 01 (Package restructure + config + track builder)

**Status:** ready-for-agent

- [x] `time-trial` runs headless with the stub: car drives forward, hits the wall, resets to the centerline, pauses 0.5 s, ghosts 1.5 s, and DNFs at max crashes; results print with crash count and DNF reason
- [x] A car commanded straight at constant speed stays on a straight (engine-seam test through the deterministic headless entry point)
- [x] Crash cycle is exact: reset pose = nearest centerline pose, pause precedes ghost, 2.0 s total before racing resumes (engine-seam test)
- [x] A lap counts only on start/finish crossing after the mid-track checkpoint; oscillating over the line without the checkpoint counts nothing (engine-seam test with a scripted controller fixture)
- [x] DNF fires on timeout and on max crashes; results include finish order, total time, best/last lap, DNF reason
- [x] Engine is deterministic: same track + controllers + config → identical results across two runs (test)
- [x] Controller API: file → single concrete controller class → instance; internal state between ticks allowed; open-loop stub lives in the controllers folder

## Comments

- 2026-08-27: implemented, all seven checklist items covered in `tests/test_engine.py` (engine seam), `tests/test_controller.py` (loader), `tests/test_cli.py` (CLI). Two deliberate deviations, both noted in the code-review summary: (1) loader *rejection* paths are tested directly rather than through a race, since a malformed file never reaches the engine — the happy path (file → instance → race) is tested through the engine as the spec asks; (2) pause/ghost timers advance before the wall check, so a car that returns to RACING is wall-checked on the same tick — the ticket's per-tick order lists no timers, and this ordering is what makes the crash cycle exactly 80 ticks. JAX warmup compiles every batch shape 1..N so mid-race terminal transitions don't recompile (measured worst tick 0.6 ms in a 2-car race).
