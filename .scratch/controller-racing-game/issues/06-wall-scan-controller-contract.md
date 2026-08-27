# 06: Wall scan + controller contract

**What to build:** The sensor, first half. Every tick each vehicle receives a full-360° laser scan: 72 beams at 5° spacing, no max range — a ray stops at the first obstacle. Beams march the occupancy grid (vectorized in numpy, uniform sampling at grid resolution). No-hit beams report `np.inf` in-process. The scan is wired into the controller contract: the per-tick step now receives the scan alongside the state, and the base class, the loader's concreteness check, and the open-loop stub update accordingly. The scan is handed to every vehicle whose controller is stepped (RACING + GHOST, per 05). Vehicle visibility in the scan lands in 07.

**Blocked by:** 05 (Ghost driving — behaviour change)

**Status:** ready-for-agent

- [x] A vehicle facing a known wall reads the correct distance on the beam(s) pointing at it (engine-seam test with known geometry)
- [x] Beams with no obstacle report `np.inf`
- [x] The scan is computed vectorized in numpy (no per-beam Python loop)
- [x] Controllers receive the scan every tick; `time-trial` still runs headless E2E with the stub, updated to the new signature

## Comments

- 2026-08-27 — Implemented. New module `cocoracer/sensor.py` (`scan_walls(track, poses, beam_angles)`), called once per tick from the engine for all stepped vehicles in a single batched numpy march; the loader now rejects `step` overrides that don't take the scan.
  - Beam convention: beam 0 is straight ahead, beam i at heading + i·(360/len(scan))° counter-clockwise. Documented on `Controller`.
  - No-hit = `np.inf`. A hit is the first in-grid occupied cell; a ray that leaves the grid without hitting is a no-hit (the grid is all the sensor knows). This also covers ghost poses driven through a wall, past the grid.
  - The march is vectorized over beams × vehicles per distance step; the Python loop iterates distance steps only. Escaped rays are killed via a convex-grid distance test so out-of-grid poses terminate.
  - Measured cost (this machine, 72 beams): stadium 8 vehicles 3.4 ms/tick, spa 8 vehicles 7.9 ms/tick at a worst-case centerline pose.
  - Deviations: `np.inf` is exercised with synthetic grids in `tests/test_sensor.py` (real closed tracks fill the whole outer band, so no in-grid ray goes unhit); distance assertions tolerate 1.5 grid resolutions because occupancy is judged at cell centers and the first occupied sample can sit one full step past the wall face; added a loader test that the old 5-arg signature is rejected; `docs/coding-style.md` module layout now lists `sensor.py`.
