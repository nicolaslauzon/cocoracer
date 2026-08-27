# 13: Web front end

**What to build:** The front end is a single static page with a plain-canvas renderer (vanilla JS, no framework, no build step): the track is prerendered to an offscreen canvas once from the static message; each dynamic message redraws only the cars (rotated by heading) and the HUD (lap, speed, status racing/paused/ghost/finished/DNF, crash count, best/last lap, race timer). The static/dynamic split is the scaling seam: the appearance can be reskinned later without touching the sim or the protocol.

**Blocked by:** 12 (Web protocol + server)

**Status:** ready-for-agent

- [ ] The track is rendered once (offscreen prerender), cars animate with correct heading, and the HUD updates on each dynamic message
- [ ] The HUD shows lap, speed, status, crash count, best/last lap, and the race timer
- [ ] The page is a single static asset — no build step, no JS framework
