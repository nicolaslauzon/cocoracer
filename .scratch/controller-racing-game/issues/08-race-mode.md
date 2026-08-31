# 08: Race mode

**What to build:** The race mode for two or more controllers. Vehicles start on a staggered grid behind the start/finish line after a countdown; at countdown end the lap trackers restart from the grid pose so no lap is booked during the countdown. Vehicle-to-vehicle collision (distance threshold) triggers the same reset → pause → ghost flow as a wall crash; ghost vehicles cannot be hit. The race continues until every vehicle has finished or the time limit expires; the results table ranks by finish time with DNFs last and their reason. The `race` CLI subcommand takes the track and comma-separated controller files.

**Blocked by:** 07 (Vehicle visibility in scan)

**Status:** done

- [x] `race` CLI runs two controllers end-to-end headless with grid + countdown; the results table prints
- [x] Vehicle-to-vehicle collision triggers the same reset/pause/ghost flow as a wall crash (engine-seam test with two scripted vehicles); a ghost vehicle cannot be re-collided
- [x] Lap timing starts at countdown end: trackers restart from the grid pose
- [x] The race ends only when all vehicles finish or on timeout; ranking is by finish time, DNFs last with reason

## Comments

- 2026-08-27 — Done. `RaceEngine` and `run_race` take `mode="time-trial" | "race"` (unknown values raise `ValueError`). Race mode parks vehicle `i` on the centerline at arc length `(track_length - (i + 1) * grid_spacing) % track_length`, holds every vehicle through the countdown (time advances, controllers silent, speeds zero), then releases: lap trackers re-anchor at the grid poses so the first lap is timed from the release and nothing books during the countdown. `_check_collisions` runs each tick over RACING pairs only: below `collision_distance` both cars go through the same reset → pause → ghost flow as a wall crash, and non-racing cars are excluded so ghosts cannot be hit or re-hit. The race ends when every vehicle is terminal or the time limit expires; the results table ranks by finish time with DNFs last and their reason. The `race` CLI subcommand takes the track and comma-separated controller files, disambiguates duplicate file stems as `stem (n)`, and runs headless. New tests: engine-seam tests for the staggered grid, the countdown hold, lap timing from release, v2v crash with lockstep pause/ghost and no ghost re-collision, timeout DNF ranking, and two finishers ranked by finish time with the race ending on the last crossing; CLI tests for a headless two-controller race, single-controller rejection, and a missing controller file. All four checks pass (113 tests, was 104).
