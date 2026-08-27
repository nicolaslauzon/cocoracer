# 08: Web dashboard

**What to build:** The live web view of a race. A web server thread runs beside the sim loop and streams two message kinds over WebSocket: on connect, one static message (centerline, occupancy grid as origin/resolution/occupied cells, track width, start line); then a dynamic snapshot every ~150 ms (sim time, phase, countdown, per-vehicle id/name/position/heading/speed/steering/lap/status/best lap/last lap/crash count/finish time). The front end is a single static page with a plain-canvas renderer (vanilla JS, no framework, no build step): the track is prerendered to an offscreen canvas once from the static message; each dynamic message redraws only the cars (rotated by heading) and the HUD (lap, speed, status racing/paused/ghost/finished/DNF, crash count, best/last lap, race timer). `null` in JSON stands for a no-hit beam. The static/dynamic split is the scaling seam: the appearance can be reskinned later without touching the sim or the protocol.

**Blocked by:** 04 (Race mode + pure-pursuit reference)

**Status:** ready-for-agent

- [ ] A running race is watchable live in the browser: track rendered once, cars animate with correct heading, HUD updates
- [ ] Protocol: one static message on connect, then dynamic snapshots only; `null` for no-hit; all vehicle statuses (racing, paused, ghost, finished, DNF) are represented
- [ ] The protocol serializer is a pure function and is tested for the static and dynamic message shapes (no server/socket tests)
- [ ] The headless flag disables the web view; the race runs identically with and without it
- [ ] The page is a single static asset — no build step, no JS framework
