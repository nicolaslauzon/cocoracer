# 12: Web protocol + server

**What to build:** A web server thread runs beside the sim loop and streams two message kinds over WebSocket: on connect, one static message (centerline, occupancy grid as origin/resolution/occupied cells, track width, start line); then a dynamic snapshot every ~150 ms (sim time, phase, countdown, per-vehicle id/name/position/heading/speed/steering/lap/status/best lap/last lap/crash count/finish time). `null` in JSON stands for a no-hit beam. The protocol serializer is a pure function (state → JSON) and is tested for the static and dynamic message shapes — no server or socket tests. Phase and countdown come from the engine; the static message reads `Track` fields directly. CLI wiring: the web view is on by default, and the headless flag disables it with the race running identically either way. A minimal static page is served so a live race is watchable in the browser (basic track outline + car dots + status text; the full renderer lands in 13).

**Blocked by:** 08 (Race mode), 11 (RaceSnapshot)

**Status:** ready-for-agent

- [ ] Protocol: one static message on connect, then dynamic snapshots only; `null` for no-hit; all vehicle statuses (racing, paused, ghost, finished, DNF) are represented
- [ ] The protocol serializer is a pure function and is tested for the static and dynamic message shapes (no server/socket tests)
- [ ] A running race is watchable live in the browser: cars move as the race progresses
- [ ] The headless flag disables the web view; the race runs identically with and without it
