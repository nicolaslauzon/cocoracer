# 03: Extract RaceState

**What to build:** The crash / pause / ghost / DNF rules and the per-vehicle race record are currently inlined in the race engine. They move into `cocoracer/race_state.py`: `RaceState(pause_ticks, ghost_ticks, max_crashes, laps_target)` holds status, DNF reason, both timers, crash count, laps completed, best/last lap, and finish time. Methods: `advance()` (Pause → Ghost → RACING timers, called every tick for every vehicle); `crash() -> bool` (adds a crash; True = DNF at the crash limit — the engine then applies the physical reset: nearest centerline pose, zero speed/steering/targets, and tracker resync); `timeout()` (DNF, reason TIMEOUT); `record_lap(lap_time, time)` (adds the lap, updates best/last; FINISHED + finish time at the lap target). Two rules: `may_step` = RACING (GHOST is added in 05); `is_racing` = RACING — the one rule for visibility, collision, and lap booking; a named `is_visible` is added only if those ever diverge. `VehicleStatus` and `DnfReason` move here and are re-exported from `cocoracer`. `Vehicle` keeps only name, controller, pose, speed, steering, per-tick targets, and one `RaceState` (the tracker lands in 04). Pure move: no behaviour change, results identical.

**Blocked by:** None (can start immediately; 02 is done)

**Status:** done

- [x] `RaceState` owns the max-crashes DNF, the timeout DNF, and the finish rule (FINISHED + finish time at the lap target)
- [x] `tests/test_race_state.py` pins the 80-tick cycle (20 Pause + 60 Ghost) with no engine, driver, or track: `crash()` → 20×`advance()` → 60×`advance()` → RACING
- [x] `Vehicle` keeps only name, controller, pose, speed, steering, targets, `state`; `is_racing` moves to `RaceState`
- [x] `VehicleStatus` / `DnfReason` move to `race_state.py` and are re-exported from `cocoracer`
- [x] No behaviour change: all existing engine seam and CLI tests stay green

## Comments

- 2026-08-27 — Done. New `cocoracer/race_state.py` with `RaceState(pause_ticks, ghost_ticks, max_crashes, laps_target)` owning status, DNF reason, both timers, crash count, laps, best/last lap, and finish time; methods `advance()`, `crash() -> bool`, `timeout()`, `record_lap(lap_time, time)`, properties `may_step`/`is_racing` (both RACING for now). `VehicleStatus`/`DnfReason` moved there and are re-exported from `cocoracer`. `Vehicle` now holds name, controller, `state`, pose, speed, steering, targets; `RaceEngine` builds each vehicle's `RaceState` from the race config. Deviations, all deliberate: (1) `Vehicle` still carries the three private lap-tracking fields (`_prev_s`, `_checkpoint_passed`, `_lap_start`) since the tracker itself lands in 04; (2) vehicle construction moved after the config-derived attributes in `RaceEngine.__init__`, because `state` needs pause/ghost/crash/lap values; (3) `cocoracer/engine.py` keeps importing `DnfReason`/`VehicleStatus` (needed to type `VehicleResult`), so `from cocoracer.engine import ...` lines in existing tests still resolve unchanged. `tests/test_race_state.py` adds 6 tests including the pinned 80-tick cycle (19 PAUSED + 60 GHOST + RACING) with no engine, driver, or track; existing `test_engine.py` assertions kept verbatim with attribute paths updated to `v.state.*`. All four checks pass (84 tests, was 78).
