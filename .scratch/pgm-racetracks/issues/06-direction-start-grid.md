# 06: Direction key, start line, occupancy grid, and end-to-end map build

**What to build:** the map track kind builds end to end from its three files (PGM image, centerline CSV, metadata YAML). The driving direction is a required per-track param-file key (`cw` or `ccw`, as seen on the map image); the builder determines the centerline's inherent travel direction from its point order and, if the key disagrees, reverses the point order (which also swaps the derived left/right walls). Reversing the key therefore reverses the centerline and swaps the walls. The occupancy grid is the drivable mask (largest connected component) upsampled 2×, giving 0.3 m cells in track world. The start/finish line is placed at the player's marked pixel: a required `start: [col, row]` config key per map track in image pixels (row 0 is the top of the image); the builder converts the pixel to track world and re-fits the centerline and walls so the nearest centerline point sits at s=0. The mid-track checkpoint stays at s = length/2. The map track kind is wired through config (a `maps` section holding per-track map path, threshold, scale, direction, and start pixel) and the track build dispatch; a map track without a direction key or a start key is a config error.

**Blocked by:** 05 (centerline file, parse, scale, and wall derivation).

**Status:** ready-for-agent

- [ ] A synthetic map builds end to end: three files → Frenet-ready track with derived walls and the drivable mask (upsampled 2×, 0.3 m cells) as the occupancy grid
- [ ] Direction key is honored: reversing it reverses the centerline and swaps the left/right walls
- [ ] Start line lands at the configured pixel (nearest centerline point at s=0) with the correct heading; checkpoint at length/2
- [ ] `maps` config section loads: defaults apply, per-track overrides win, a map track without a direction key or a start key is a config error
- [ ] The four checks are green
