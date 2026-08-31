# 19: Crash mechanic

**What to build:** The crash consequence lives on the vehicle record: `Vehicle.crash(track)` zeroes the motion, registers the crash with the race state (pause, or DNF at the crash limit), and — unless it is a DNF — resets the vehicle to the nearest centerline pose with the lap tracker resynced there. Detection is one call, `collide(track, fleet, length, width, collision_distance)` in a new `collision.py`: racing vehicles whose footprint touches a wall, then racing vehicle pairs closer than the collision distance, in fleet order; each vehicle takes at most one crash per tick, and a vehicle that has already crashed drops out of the remaining pairs (replaces the old snapshot ordering, where a vehicle could be crashed twice in one tick). The engine's `_check_walls`, `_check_collisions`, and `_handle_crash` collapse into one wiring loop.

**Blocked by:** 18

**Status:** done

- [x] `Vehicle.crash(track)` owns the full consequence; DNF skips the reset
- [x] `collide` reports wall hits before vehicle hits; at most one entry per vehicle
- [x] Ghosts and paused vehicles neither hit nor are hit
- [x] A racing car overlapping a ghost does not crash (test moves to the collision seam)
- [x] Engine crash tests keep pinning the wiring; determinism fingerprint green

## Comments

- 2026-08-27 — Done. `Vehicle.crash(track) -> bool` (cocoracer/vehicle.py) owns the whole consequence, exactly mirroring the old engine's `_handle_crash`: register with `state.crash()`, zero speed/steering/targets, and unless DNF reset to `track.nearest_centerline` with `tracker.resync`. `collide` in the new `cocoracer/collision.py` runs the wall pass over the racing vehicles (footprint against the occupancy grid), then the pair pass over the wall-crash-free pool in fleet (i, j) order; a `done` set of `id(v)` makes each vehicle take at most one crash per tick. The engine's three crash methods collapse into `_check_crashes`, a wiring loop over `collide` + `crash`; the tick order is otherwise unchanged. Deliberate behavior change (the one the review flagged as worth pinning): in a chain — three racing cars all within the collision distance of their neighbours — the old snapshot ordering crashed the middle car twice in one tick; now the (a, b) pair consumes it and (b, c) is skipped, so the third car survives that tick. Pinned by `test_a_vehicle_takes_at_most_one_crash_per_tick` and `test_wall_hits_drop_out_of_the_pair_pass`. Tests: `tests/test_collision.py` at the `collide` seam (wall hit, ghost/paused inert, pair below/at distance, overlapping ghost and paused, wall-before-pair ordering); `tests/test_vehicle.py` gains the crash-consequence tests (reset to centerline + pause, DNF skips the reset); the engine's `test_racing_car_overlapping_ghost_does_not_crash` moved to the seam. The engine crash tests (`test_crash_resets_to_centerline_then_pause_and_ghost`, `test_ghost_passes_through_wall_without_crashing`, `test_max_crashes_dnfs`, `test_open_loop_stub_crashes_out`, `test_snapshot_reports_racing_and_crashed_vehicles`) keep pinning the wiring. The chain case is the only input where behavior differs, and it is unreachable in the deterministic time-trial fingerprint, which stays green. `CONTEXT.md` gained the Crash term; `docs/coding-style.md` module layout updated.
