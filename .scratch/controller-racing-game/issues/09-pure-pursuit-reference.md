# 09: Pure-pursuit reference

**What to build:** The pure-pursuit baseline ported from the old experiment to the new controller API: centerline following with speed-scaled lookahead — the first controller to complete a lap-based race, and the strong reference every player tries to beat.

**Blocked by:** 08 (Race mode)

**Status:** ready-for-agent

- [ ] Pure pursuit completes N laps on the stadium track (the first winning run of a lap-based race)
- [ ] Head2head pure pursuit vs open-loop stub: pure pursuit finishes, stub DNFs
- [ ] Pure-pursuit gains are parameters in the param file under its own baseline block
