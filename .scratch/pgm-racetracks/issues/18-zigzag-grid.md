# 18: F1-style zigzag starting grid

**What to build:** the starting grid is a hardcoded F1-style zigzag, identical on every track: the pole car is on the centerline one row (3.75 m) behind the start/finish line, and each car after it is one row (3.75 m) back, alternating ±2.5 m left and right of the centerline. The geometry is a code constant in the engine's grid builder, not configuration — `grid_spacing` is removed from the param-file race block and the config loader (the longitudinal 3.75 m row spacing survives as a hardcoded constant).

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Grid poses on any track (stadium and a synthetic track): pole on the centerline 3.75 m behind the line, then ±2.5 m alternating at 3.75 m rows
- [x] `grid_spacing` is gone from the param file and the config loader; existing params load without it
- [x] The engine tests assert the zigzag geometry
- [x] The four checks are green
