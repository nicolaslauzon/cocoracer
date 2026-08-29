# 07: Ship the three maps

**What to build:** the three map sets that ship in `maps/` (PGM image + centerline CSV + metadata YAML each) become the game's map tracks — `right-interior`, `icra-2023-short`, `icra-2025` — selectable by name from the CLI. The param entries set each map's `direction` key to the CSV's point order, so shipped tracks run the direction the files were authored in. One global scale of 0.6 m per pixel (12× the native 0.05 m/px; param-file `maps` section, per-track override) makes the numbers real-life in magnitude: corridors are 13–40 m and the ~2 m car is about one eighth of the narrowest.

**Blocked by:** 06 (direction key, start line, occupancy grid, and end-to-end map build).

**Status:** ready-for-agent

- [ ] All three maps build at construction with no errors; derived walls pass the mask consistency check
- [ ] Each map's median width matches the CSV's `w_left + w_right` scaled to track world within tolerance (right-interior ~20 m, icra-2023-short ~20 m, icra-2025 ~17 m)
- [ ] Each map's start line is on a straight and its direction matches the param-file key
- [ ] A brief headless run ticks cleanly on each map (full lap-progress bar arrives in ticket 17)
- [ ] The default track is unchanged until ticket 16 flips it
