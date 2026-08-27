# 03: Laser scan + ghost visibility

**What to build:** The sensor. Every tick each vehicle receives a full-360° laser scan: 72 beams at 5° spacing, no max range — a ray stops at the first obstacle. Beams march the occupancy grid (vectorized in numpy, uniform sampling at grid resolution) and also test closed-form ray-circle intersection against every non-ghost vehicle (radius = the collision distance); the first hit wins. Ghost vehicles are excluded from scans entirely. No-hit beams report `np.inf` in-process. The scan is wired into the controller contract: the per-tick step now receives the scan alongside the state, and the stub/contract update accordingly.

**Blocked by:** 02 (Headless engine, dynamics & race rules)

**Status:** ready-for-agent

- [ ] A vehicle facing a known wall reads the correct distance on the beam(s) pointing at it (engine-seam test with known geometry)
- [ ] A non-ghost vehicle appears in another vehicle's scan at the correct distance; a ghost vehicle is absent from the scan (engine-seam tests)
- [ ] Beams with no obstacle report `np.inf`
- [ ] The scan is computed vectorized (numpy); scan cost for 8 vehicles stays well under the tick budget (perf assertion)
- [ ] Controllers receive the scan every tick; `time-trial` still runs headless E2E with the stub
