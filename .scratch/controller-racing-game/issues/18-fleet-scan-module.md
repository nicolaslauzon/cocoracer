# 18: Fleet scan module

**What to build:** One deep module for the laser scan pipeline. `fleet_scan(track, fleet, beam_angles, collision_distance)` in `sensor.py` returns the full-circle scan for every vehicle in a fleet: walls (marched over the track's occupancy grid) plus the collision circles of the racing vehicles, first hit wins per beam, a no-hit beam reads inf. Only racing vehicles block a beam; no vehicle sees itself. The wall march moves into `track.py` as `Track.beam_distances`, next to the other geometry queries, so `sensor.py` no longer touches the grid. The `Vehicle` record moves from `engine.py` into its own `vehicle.py` so the scan module can type its fleet without importing the engine. The engine's `_step_controllers` shrinks to: filter the stepable vehicles, one `fleet_scan` call, step the controllers.

**Blocked by:** (none)

**Status:** done

- [x] `fleet_scan` returns (N, B) aligned to the fleet; first hit wins; no hit reads inf
- [x] Only racing vehicles block a beam; no vehicle sees itself
- [x] `Track.beam_distances` owns the grid march; `sensor.py` no longer touches the grid
- [x] `Vehicle` lives in `cocoracer/vehicle.py`, re-exported from `engine` and the package
- [x] Visibility tests move to the scan seam (no engine, no countdown, no dynamics); one engine wiring pin remains
- [x] Determinism fingerprint and full suite green

## Comments

- 2026-08-27 — Done. `sensor.py` now exposes one function, `fleet_scan(track, fleet, beam_angles, collision_distance) -> (N, B)`: walls from `Track.beam_distances` (the grid march moved to `track.py:beam_distances`, next to `footprint_in_wall`, with the convex-grid early exit) merged by `np.minimum` with the vehicle circles from a private `_vehicle_hits` (the old `scan_vehicles` body, unchanged math). Visibility is derived from the fleet itself: targets are the RACING vehicles of the fleet, and each racing scanner is excluded by an index array built in the same pass (no `id()` map); since racing implies steppable, the engine's `may_step` filter and the old `racing` set are the same population. The `Vehicle` record moved to `cocoracer/vehicle.py`; `engine.py` and `cocoracer/__init__.py` import it from there (`cocoracer.engine.Vehicle` still resolves). The engine's `_step_controllers` is now filter, one `fleet_scan` call, step. Tests: the five wall-march tests moved to `tests/test_track.py` as `beam_distances` tests (synthetic grids via a shared `synthetic_track_factory` fixture in `conftest.py`); `tests/test_sensor.py` is rewritten at the scan seam (row alignment, visibility policy, first-hit merge — no engine, no countdown, no dynamics); `tests/test_vehicle.py` added for the record. The engine keeps one wiring pin (`test_scan_arrives_every_tick_while_steppable`). Numerics are untouched, so the determinism fingerprint and the full suite pass unchanged.
