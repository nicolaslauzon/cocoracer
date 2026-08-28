# 07: Ship the three maps

**What to build:** the three PGM images that ship in the repo become the game's map tracks — `right-interior`, `icra-2023-short`, `icra-2025` — selectable by name from the CLI. One global scale of 0.6 m per pixel (param-file `maps` section, per-track override) makes the numbers real-life in magnitude: the narrowest corridor (26 px median) is 15.6 m and the ~2 m car is about one eighth of it.

**Blocked by:** 06 (midline centerline, direction key, and start line).

**Status:** ready-for-agent

- [ ] All three maps build at construction: single ring, one hole, no errors
- [ ] Each map's median width matches the measured pixel widths times 0.6 m/px within tolerance (right-interior ~36 px, icra-2023-short ~40 px, icra-2025 ~26 px)
- [ ] Each map's start line is on a straight and its direction matches the param-file key
- [ ] A brief headless run ticks cleanly on each map (full lap-progress bar arrives in ticket 17)
- [ ] The default track is unchanged until ticket 16 flips it
