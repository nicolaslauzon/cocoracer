# 13: Web front end

**What to build:** The front end is a single static page with a plain-canvas renderer (vanilla JS, no framework, no build step): the track is prerendered to an offscreen canvas once from the static message; each dynamic message redraws only the cars (rotated by heading) and the HUD (lap, speed, status racing/paused/ghost/finished/DNF, crash count, best/last lap, race timer). The static/dynamic split is the scaling seam: the appearance can be reskinned later without touching the sim or the protocol.

**Blocked by:** 12 (Web protocol + server)

**Status:** done

- [x] The track is rendered once (offscreen prerender), cars animate with correct heading, and the HUD updates on each dynamic message
- [x] The HUD shows lap, speed, status, crash count, best/last lap, and the race timer
- [x] The page is a single static asset — no build step, no JS framework

## Comments

- 2026-08-27: Done in `wt-13`. `cocoracer/web/index.html` is now a single
  static page: vanilla JS on canvas, no framework, no build step, no network
  fetches beyond the WebSocket.
  - The static message prerenders the track once to an offscreen canvas
    (occupied grid cells, a road ribbon stroked to `track_width` along the
    centerline with a dashed centerline, and the start line); each dynamic
    message blits that layer and redraws only the cars and HUD, so reskinning
    later touches neither sim nor protocol.
  - Cars are capsules (round-capped strokes) rotated to their heading,
    colored by status — racing blue, paused red, finished green, DNF orange —
    with ghosts at 40% opacity.
  - The HUD shows the race clock, phase, and countdown (a large overlay digit
    while counting down), plus per vehicle: name, status, lap, speed,
    steering, crash count, best/last lap, and finish time when present.
  - Tests: `tests/test_web_frontend.py` checks the page exists, pulls nothing
    external, targets the `/ws` path, and references every field name the
    serializers emit (names extracted from `protocol.py` at test time, so a
    renamed key fails) and every `VehicleStatus` value.
  - Deviation: `scan` arrives with each vehicle but is not rendered — the
    issue's render list is cars plus HUD; the test whitelists it as unused.
