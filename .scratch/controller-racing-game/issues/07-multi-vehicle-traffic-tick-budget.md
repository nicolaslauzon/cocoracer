# 07: Multi-vehicle traffic + tick budget

**What to build:** Full N-vehicle racing (3+ controllers at once). The start grid accommodates N vehicles; a pack drives together with all traffic behavior — vehicle-to-vehicle collisions, crash resets, ghost phases in the middle of traffic, DNF propagation — and the results table stays valid for every participant. The real-time guarantee is proven: a perf test races 8 vehicles on the stadium and asserts the tick cost stays inside the 25 ms budget.

**Blocked by:** 04 (Race mode + pure-pursuit reference)

**Status:** ready-for-agent

- [ ] `race` CLI runs N ≥ 3 controllers end-to-end headless with a valid results table for all vehicles
- [ ] Crash/ghost behavior is correct in traffic (engine-seam test: a colliding vehicle resets to the centerline; a ghost vehicle cannot be re-collided; non-ghost vehicles remain visible in scans)
- [ ] Perf test: 8 vehicles complete the stadium within the 25 ms per-tick budget (measured and asserted)
- [ ] The race remains deterministic with N vehicles (same inputs → same results)
