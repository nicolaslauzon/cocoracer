# 02: Real-scale vehicle and race block

**What to build:** one global vehicle with real-life dimensions and limits: width 2.0 m, length 2.5 m, wheelbase 1.65 m (lf 0.79 / lr 0.86), max speed 25 m/s (~90 km/h), max acceleration 8 m/s², max steering ±0.5 rad at ±4 rad/s. The race block is re-derived: collision distance 2.5 m, grid spacing 3.75 m, time limit 600 s; laps, crash pause, ghost duration, crash limit, and countdown unchanged. The stadium is rescaled ×20 (width 20 m, straights 120 m, turn radius 40 m) so the 2 m car fits.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Vehicle geometry and limits come from the param file; minimum turning radius (~3.2 m) clears the tightest stadium corners
- [ ] Collision distance, grid spacing, and time limit updated; unchanged values (laps, pause, ghost, crash limit, countdown) untouched
- [ ] Stadium rescaled and still builds, reports its width, and a headless time-trial ticks cleanly to completion (lap progress bar arrives in ticket 17)
- [ ] All four checks green
