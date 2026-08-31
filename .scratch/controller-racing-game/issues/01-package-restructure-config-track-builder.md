# 01: Package restructure + config + track builder

**What to build:** The repo is restructured from experimental scripts into a proper package. A single YAML param file becomes the source of truth for the whole game (sim tick, vehicle physics and control limits, sensor beam count, race rules, track width/resolution, per-baseline gain blocks) and loads into typed config objects. A CLI entry point exposes `time-trial` and `race` subcommands (for now: parse, resolve the track, report the selected config and track geometry). A track builder composes straight and turn segments, validates closure, and produces the resampled centerline, Frenet coordinates, and the occupancy grid (wall = cell beyond half track width from the centerline). The first closed track (a stadium: two straights + two 180° turns) is defined in the param file. Old experimental files are removed (their algorithms survive in git history and get re-ported as baselines later).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Repo is a package; old experimental scripts removed; dependencies updated (add YAML parsing, web server, pytest; drop teleop/matplotlib deps)
- [x] All game settings live in the one param file and load into typed config objects
- [x] CLI parses `time-trial` and `race` with track and controller arguments and reports the resolved config and track geometry
- [x] Track builder validates closure (turn angles sum to ±360°, endpoints close); a malformed spec fails loudly with a clear error
- [x] Stadium track builds: resampled centerline, Frenet roundtrip (Cartesian → Frenet → Cartesian) returns the same point, occupancy grid marks exactly the cells beyond half-width from the centerline
- [x] Track-seam tests pass: closure rejection, Frenet roundtrip, grid-vs-half-width

## Comments

Work landed in the initial restructure (`f67a4e7`); boxes ticked on 2026-08-28 to bring the tracker in line with the rest.
