# 05: Ghost driving — behaviour change

**What to build:** During Ghost (1.5 s after a crash) the vehicle's controller is stepped and the vehicle drives, but the vehicle is hidden from laser scans, cannot be hit, does not book laps, and passes through walls. A crash now costs about 0.5 s (the Pause) of racing time instead of 2.0 s. Durations stay in the YAML.

| Status | Controller stepped | Visible / can be hit / books laps |
|---|---|---|
| RACING | yes | yes |
| PAUSED (0.5 s) | no | no |
| GHOST (1.5 s) | yes | no |
| FINISHED / DNF | no | no |

`may_step` = RACING or GHOST (the controller gate); `is_racing` = RACING (the one rule for visibility, collision, and lap booking).

Engine tick, in order: step the controllers that `may_step` → integrate the non-terminal vehicles → `advance()` → wall-check the RACING vehicles → `feed()` the RACING trackers → `record_lap` → timeout check.

Docs are part of this ticket: `CONTEXT.md` — the Ghost entry gains "the controller is still stepped; the vehicle passes through walls", and the Tick entry changes from "every racing controller" to every controller that may be stepped (RACING + GHOST); `docs/coding-style.md` — the module layout lists `race_state.py` and `lap_tracker.py`.

**Blocked by:** 03 (Extract RaceState), 04 (Extract LapTracker)

**Status:** ready-for-agent

- [x] A Ghost vehicle is driven by its controller during the 1.5 s Ghost phase (engine-seam test with a scripted driver); the wall check and the lap feed skip it (the vehicle-collision gate lands with 08)
- [x] `may_step` = RACING or GHOST, `is_racing` = RACING; the crash costs pause-only time (the ghost phase overlaps with driving)
- [x] Engine tick follows the order above
- [x] `CONTEXT.md` Ghost + Tick entries updated; `docs/coding-style.md` layout lists the two new modules
- [x] All four checks green: `ruff format .`, `ruff check .`, `mypy cocoracer tests`, `pytest`

## Comments

- 2026-08-27 — Done. Core change is one property: `RaceState.may_step` is now RACING or GHOST (`cocoracer/race_state.py`); `is_racing` stays RACING. Verified the engine tick already matches the ticket's order, so no engine logic changed: `_step_controllers` is gated on `may_step` (ghosts now stepped), `_integrate` uses the non-terminal set (ghosts are integrated, so they drive), `_check_walls` and `_book_laps` are gated on `is_racing` (ghosts skipped for wall checks and lap feed). Only the `engine.py` module docstring and the `Controller` base-class docstring were updated to say "racing or ghost". `CONTEXT.md`: Ghost entry gained "the controller is still stepped, and the vehicle passes through walls"; Tick entry now says every controller that may be stepped (racing or ghost). `docs/coding-style.md` needed no change — tickets 03/04 already listed `race_state.py` and `lap_tracker.py` in the module layout. Three new engine-seam tests in `tests/test_engine.py`: (1) ghost keeps driving — pose travels 2.7 m during the 60-tick ghost phase with no lap booked; (2) ghost passes through wall — footprint enters the wall, the ghost keeps driving >0.5 m through it with no crash counter increment, and it re-crashes the moment it returns to RACING (crashes 1 → 2); (3) a RACING car teleported onto a ghost (sustained overlap below `collision_distance` for 10 ticks) does not crash and the ghost's crash count stays 1. Deliberate deviations / notes: (a) one existing expectation was superseded — `test_crash_resets_to_centerline_then_pause_and_ghost` previously asserted `RACING` at tick 80; the ghost now ends its phase inside the wall, so that tick is `PAUSED` with `crashes == 2` (the 80-tick state-machine cycle in `tests/test_race_state.py` is untouched, as predicted); (b) `test_may_step_and_is_racing_are_racing_only` was renamed and extended to cover GHOST (may_step true, is_racing false) and FINISHED, since its old name/expectation contradicted the new contract; (c) "crash costs pause-only time" is asserted structurally — the ghost phase overlaps with driving (test 1 proves the overlap), so no separate timing test; (d) the lap-feed skip rides on the same `is_racing` gate as the wall check; the driving test asserts no lap during the ghost phase, but a ghost crossing the start line cannot be constructed on the stadium (a straight-line ghost path from any tangent reset point never reaches s=0), so the feed-skip is pinned by the shared gate plus the lap invariance assertion rather than a crossing scenario. All four checks pass (90 tests, was 87).
