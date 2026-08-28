# 06: Midline centerline, direction key, and start line

**What to build:** the centerline is the pointwise midline of the two matched boundary curves, from which the existing resample, periodic cubic-spline, and Frenet machinery is reused unchanged. The driving direction is a required per-track param-file key (clockwise or counterclockwise, as seen on the map image); the centerline is ordered to travel that way, and reversing the key reverses the centerline. The centerline is re-fitted so the start/finish line sits at s=0 at the middle of the longest straight (reusing ticket 01's helper); the mid-track checkpoint stays at s = length/2 and the starting grid stays staggered behind the line. The map track kind is wired through config (a `maps` section holding per-track map path, threshold, scale, and direction) and the track build dispatch; a map track without a direction key is a config error.

**Blocked by:** 03 (wall-curve track model), 05 (map topology).

**Status:** ready-for-agent

- [ ] A synthetic map builds end to end: mask → boundaries → midline → Frenet-ready track with the drivable mask (upsampled 2×) as the occupancy grid
- [ ] Direction key is honored: reversing it reverses the centerline
- [ ] Start line lands at s=0 on the longest straight with the correct heading; checkpoint at length/2
- [ ] Maps config section loads; defaults apply and per-track overrides win
- [ ] A map track without a direction key is a config error; a bad map is a track error
