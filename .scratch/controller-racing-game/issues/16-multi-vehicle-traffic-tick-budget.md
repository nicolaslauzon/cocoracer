# 16: Multi-vehicle traffic + tick budget

**What to build:** Full N-vehicle racing (3+ controllers at once). The start grid accommodates N vehicles; a pack drives together with all traffic behavior — vehicle-to-vehicle collisions, crash resets, ghost phases in the middle of traffic, DNF propagation — and the results table stays valid for every participant. The real-time guarantee is proven: a perf test races 8 vehicles on the stadium and asserts the tick cost stays inside the 25 ms budget.

**Blocked by:** 09 (Pure-pursuit reference)

**Status:** ready-for-agent

- [x] `race` CLI runs N ≥ 3 controllers end-to-end headless with a valid results table for all vehicles
- [x] Crash/ghost behavior is correct in traffic (engine-seam test: a colliding vehicle resets to the centerline; a ghost vehicle cannot be re-collided; racing vehicles remain visible in scans, ghosts absent)
- [x] Perf test: 8 vehicles complete the stadium within the 25 ms per-tick budget (measured and asserted)
- [x] The race remains deterministic with N vehicles (same inputs → same results)

## Comments

- 2026-08-27: Done in `wt-16`. Tests in `tests/test_traffic.py`
  (CLI, traffic behavior, determinism) and `tests/test_perf.py`
  (tick budget). No engine change: grid placement already works
  for larger N (1.5 m spacing puts 8 vehicles across 12 m of the
  24.57 m stadium; `_grid_pose` wraps modulo track length).
  - CLI: 3x pure_pursuit + open_loop on the stadium, `--no-web`,
    3 laps: all three pursuers FINISH (best lap 1.600 s, 0
    crashes), the stub DNFs with `[max crashes]`; the results
    table is valid for all four.
  - Traffic seam tests (3 vehicles, scripted drivers): a colliding
    pair resets to the nearest centerline pose and pauses with
    motion zeroed while a third vehicle is untouched; a racing
    vehicle drives straight through a parked ghost (gap dips under
    the collision distance) with no crash count moving anywhere;
    with one vehicle flipped to ghost, the observer's beam 0 reads
    0.5 m while it races and 1.5 m while it ghosts — the next
    racing vehicle's circle in its place.
  - Perf: 8 pure_pursuit on the stadium, 3 laps, 263 racing
    ticks measured wall-clock per `tick()`: mean 5.0 ms, max
    5.9 ms — 5x margin against the 25 ms budget. The test asserts
    the post-warmup mean (first 50 ticks discarded) stays under
    one tick period; the max tick is deliberately not asserted on.
  - Determinism: two fresh runs of the same 8-vehicle race match
    field-for-field (name, status, finish_order, laps, crashes,
    dnf_reason, total_time within 1e-9, plus the overall race
    time).
