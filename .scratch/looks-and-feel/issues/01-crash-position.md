# 01: Crash X at the true crash position

**What to build:** when a vehicle crashes, the engine records the vehicle's pose at the crash tick — before the centerline resync — and the dynamic message carries it as `last_crash: {x, y}` per vehicle (`null` before the first crash). The client anchors each crash X at the reported crash position instead of the post-reset position; the red X and the half-lap aging are unchanged. Watching a race in the web view, an X lands at the wall where the car actually crashed, not on the centerline.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] The engine records the pre-reset (x, y) at the tick a crash is registered, for wall hits and vehicle-to-vehicle hits alike
- [x] The dynamic message's per-vehicle object gains `last_crash`: `{x, y}` or `null` before any crash
- [x] The client stores each new crash mark at the reported crash position; marks still age out after half a lap of driving
- [x] Engine/protocol tests: a scripted crash asserts `last_crash` equals the pre-reset pose; a fresh race serializes `null`
- [x] Frontend structural test: the page references the `last_crash` field name
- [x] All four checks green