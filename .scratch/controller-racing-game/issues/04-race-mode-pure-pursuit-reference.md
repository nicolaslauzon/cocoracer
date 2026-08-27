# 04: Race mode + pure-pursuit reference

**What to build:** The race mode for two or more controllers. Vehicles start on a staggered grid behind the start/finish line after a countdown; vehicle-to-vehicle collision (distance threshold) triggers the same reset → pause → ghost flow as a wall crash. The race continues until every vehicle has finished or the time limit expires; the results table ranks by finish time with DNFs last and their reason. The pure-pursuit baseline is ported from the old experiment to the new controller API: centerline following with speed-scaled lookahead — the first controller to complete a lap-based race, and the strong reference every player tries to beat.

**Blocked by:** 03 (Laser scan + ghost visibility)

**Status:** ready-for-agent

- [ ] `race` CLI runs two controllers end-to-end headless with grid + countdown; the results table prints
- [ ] Pure pursuit completes N laps on the stadium track (the first winning run of a lap-based race)
- [ ] Vehicle-to-vehicle collision triggers the same reset/pause/ghost flow as a wall crash (engine-seam test with two scripted vehicles)
- [ ] Head2head pure pursuit vs open-loop stub: pure pursuit finishes, stub DNFs
- [ ] The race ends only when all vehicles finish or on timeout; ranking is by finish time, DNFs last with reason
