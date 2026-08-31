# 03: Wall-curve track model

**What to build:** a track is now a centerline, two closed wall boundary curves (left/right relative to the driving direction), and a wall occupancy grid. The constant half-width concept is gone; track width is the median wall-to-wall distance along the centerline and is what the CLI reports. The stadium and centerline-JSON paths keep working by synthesizing walls at ±width/2 around the centerline (the constant-width special case). The occupancy grid is built from the wall curves at 0.3 m cells. The track-info passed to controllers keeps its shape, with width now the median. Frenet queries, the lap tracker, and beam ray-march are untouched.

**Blocked by:** 02 (real-scale vehicle and rescaled stadium).

**Status:** done

- [x] Track exposes centerline, left/right wall curves, and the occupancy grid; no constant half-width remains
- [x] Stadium and centerline-JSON tracks build with synthesized ±width/2 walls; reported width equals the configured width
- [x] Existing F1 tracks build and report a median width within tolerance of their old constant width
- [x] Grid is 0.3 m cells; collision and laser-scan behavior on existing tracks unchanged
- [x] Controller contract tests pass unchanged; tick-budget performance test green
