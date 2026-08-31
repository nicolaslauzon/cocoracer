# 20: Frenet plumbing into the vehicle record

**What to build:** The vehicle record owns its position on the centerline. The engine currently converts poses to Frenet arc length in three places (`__init__`, `_release`, `_book_laps`) and threads the `s` to the lap tracker, discarding two of the three `to_frenet` outputs at every call site; the lap-feeding policy — RACING vehicles only — lives in the engine's tick loop. The record gains `anchor(track, time)` (race start and countdown release) and `record(track, time)` (per-tick lap feeding: pose → `s`, feed the tracker, hand a booking to the race state), and the engine stops calling `to_frenet` entirely. The crash resync from issue 19 already lives on the record, so all centerline consequences share one seam.

**Blocked by:** 18, 19

**Status:** done

- [x] `anchor` re-anchors the lap tracker at the current pose and time (construction and countdown release)
- [x] `record` feeds the tracker and books the lap with the race state; non-racing vehicles are not fed
- [x] The engine no longer calls `to_frenet`; `_release` and `_book_laps` are wiring loops
- [x] Seam tests: an anchored vehicle fed across checkpoint and line books a lap timed from the anchor; a ghost vehicle's pose is not fed
- [x] Determinism fingerprint and full suite green

## Comments

- 2026-08-27 — Done. `Vehicle` (cocoracer/vehicle.py) gained two methods: `anchor(track, time)` — pose → `to_frenet`, `tracker.start(s, time)` — called at construction and on countdown release; and `record(track, time)` — the lap policy in one place: non-RACING vehicles return without feeding (ghosts and paused cars hold their tracker), otherwise pose → `to_frenet`, `tracker.feed(s, time)`, and a booking goes to `state.record_lap`, which may finish the vehicle. The engine's three `to_frenet` call sites collapsed into wiring: `__init__` calls `v.anchor(track, self.time)`, `_release` is a loop of `v.anchor(self.track, self.time)`, and `_book_laps` is a loop of `v.record(self.track, self.time)` over the active vehicles; `grep to_frenet cocoracer/engine.py` comes back empty. The report sketched `anchor(track)` without a time, but the release happens after the countdown, so the anchor needs the engine clock — the only deviation. Call order and numerics are unchanged (the RACING skip still happens before any `to_frenet` in the same order), so the determinism fingerprint is bit-identical. New seam tests in tests/test_vehicle.py on the real stadium track: an anchored vehicle fed 24 small steps across checkpoint and line books exactly one lap timed from the anchor (12.0 s); a ghost car jumped across the line is not fed, so no lap arms for the next racing feed. `docs/coding-style.md` module layout updated.
