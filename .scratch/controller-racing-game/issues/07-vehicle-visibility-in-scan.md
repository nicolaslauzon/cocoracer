# 07: Vehicle visibility in scan

**What to build:** The sensor, second half. Scan rays also test closed-form ray-circle intersection against every RACING vehicle (radius = the collision distance); the first hit wins. Non-racing vehicles (paused, ghost, finished, DNF) are excluded from scans entirely.

**Blocked by:** 06 (Wall scan + controller contract)

**Status:** ready-for-agent

- [x] A racing vehicle appears in another vehicle's scan at the correct distance (engine-seam test)
- [x] A ghost vehicle and a paused vehicle are absent from the scan (engine-seam tests)
- [x] Scan cost for 8 vehicles stays well under the tick budget (perf assertion)
- [x] `time-trial` still runs headless E2E with the stub

## Comments

- 2026-08-27 — Done. The sensor gained `scan_vehicles` (cocoracer/sensor.py): closed-form ray-circle intersection against the RACING vehicles, vectorized over scanners × beams × targets, radius = `config.race.collision_distance`. The engine's `_step_controllers` (cocoracer/engine.py) now reports `min(wall_dist, vehicle_dist)` per beam; the target set is the RACING vehicles and each scanner is excluded by index, so a vehicle never sees itself (a ghost scanner is not a target, so it sees all racing vehicles — being invisible does not make it blind). Hit convention, the judgment call the ticket left open: a hit is the near root when it is strictly positive, else the far root when it is strictly positive (origin inside the circle — two RACING cars closer than the collision distance, or cars sharing the spawn pose); t = 0 (beam touching a target exactly at the origin) is not a hit. So an exactly overlapping car reads the circle exit distance, never 0. Deliberate deviations: none from the spec; only the clipping choice above, strict t > 0 on both roots. New tests, all engine-seam in tests/test_engine.py: racing car 2 m away reads 2 − r on the aimed beam in both directions plus a no-self-visibility check (same beam reads the wall with no target present); ghost and paused cars placed at the same 2 m spot read the wall instead; perf test times 20 ticks of a warm 8-vehicle engine and asserts under the tick budget (`config.sim.tick_dt`, 25 ms) — measured ~4.3 ms per tick (wall scan ~3.4 ms, vehicle scan ~0.06 ms), 6× headroom. `test_time_trial_stub_dnf_headless` in tests/test_cli.py still passes unchanged, covering the headless E2E item. No existing tests weakened or removed; `scan_walls` and the public API are untouched.
