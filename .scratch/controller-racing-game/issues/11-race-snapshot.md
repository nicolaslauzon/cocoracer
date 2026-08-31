# 11: RaceSnapshot

**What to build:** A frozen dataclass `RaceSnapshot` in `engine.py` plus `RaceEngine.snapshot()`. Per vehicle: name, id (index), status, x, y, yaw, speed, steering, laps completed, best lap, last lap, crash count, finish time, DNF reason. Top level: sim time, track. Built on demand from the sim thread; headless and `run_race` never build it, so per-tick cost is zero. Phase and countdown are not included (they live in the engine and the web serializer reads them directly); the static web message (12) reads `Track` fields directly. `RaceSnapshot` is exported from `cocoracer`.

**Blocked by:** 10 (Dynamics seam)

**Status:** done

- [x] `RaceSnapshot` is a frozen dataclass in `engine.py` with the field list above; `engine.snapshot()` is a pure read of the current state
- [x] `run_race` and the headless path never call `snapshot()`
- [x] `RaceSnapshot` is exported from `cocoracer/__init__.py`
- [x] All four checks green: `ruff format .`, `ruff check .`, `mypy cocoracer tests`, `pytest`

## Comments

- 2026-08-27: Implemented. Added frozen dataclasses `VehicleSnapshot` (one per vehicle, field list exactly as specified; names follow the existing `VehicleResult`/`RaceState` vocabulary: `laps_completed`, `crashes`, `best_lap`, `last_lap`, `finish_time`, `dnf_reason`) and `RaceSnapshot` (`time`, `track`, `vehicles`) in `cocoracer/engine.py`, plus `RaceEngine.snapshot()` which copies current state with no side effects; `tick()`/`run()`/`run_race` are untouched, so the headless path never builds a snapshot. Deliberate deviations: `RaceSnapshot.vehicles` is a `tuple` (not `list`) to match the frozen semantics, and `VehicleSnapshot` is exported from `cocoracer/__init__.py` alongside `RaceSnapshot` since it is the public element type of the `vehicles` field that ticket 12's serializer will type against. Added two tests to `tests/test_engine.py`: one checking snapshot fields for a racing vehicle and a DNF'd vehicle (via `max_crashes=1`), one checking purity (two consecutive calls compare equal and no tick/pose/status/crash state changes).
