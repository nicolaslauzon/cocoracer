Status: ready-for-agent

# Spec: Autonomous Controller Racing Game

## Problem Statement

The repo currently holds experimental fragments (teleop demo, pure-pursuit demo, open non-closed tracks) but no playable game. The user wants a game in which the player programs the autonomous controller for an Ackermann vehicle in a single Python file and races it: time trial alone on the track, head-to-head against AI baselines, head-to-head against another player's algorithm, and N algorithms on the track at the same time. There is no race rules engine, no lap logic, no collision handling, no way to run or watch a race, and no baselines to compete against.

## Solution

The player copies a controller stub into a controllers folder and implements one class: `reset(track_info)` plus `step(x, y, yaw, speed, steering_angle, laser_scan) -> (speed, steering_angle)`, called once per tick (40 Hz) in a loop. The game drives a JAX kinematic bicycle model on closed-loop, lap-based tracks. Collisions with a wall or another vehicle reset the car to the nearest centerline point with a 0.5 s pause, followed by a 1.5 s ghost phase (invisible to laser scans, non-colliding). Three baselines ship with the game: wall follow (PID-style, F1TENTH Lab 3 semantics), gap follow (F1TENTH Lecture 5 semantics), and a pure-pursuit reference; all baseline gains are parameters. Everything — vehicle physics, sensor, race rules, baselines — is driven by one YAML param file. Races are launched from the CLI and watched on a lightweight web dashboard (static track rendered once, dynamic vehicle state at low rate, clean protocol so the front end can be reskinned without touching the sim). A deterministic headless race engine makes the whole game logic testable without web, threads, or wall clock.

## User Stories

1. As a player, I want a controller stub file to copy and implement, so that I start from a working template with the tick interface already in place.
2. As a player, I want to launch a race from the CLI by naming the track and the controller file(s), so that I never have to write a harness to test my controller.
3. As a player, I want my controller called every tick with position, heading, speed, steering angle, and a 360° laser scan, so that I can drive from local sensing alone, without a global map.
4. As a player, I want the laser scan to have no max range (a ray stops at the first obstacle), so that I don't have to interpret "max range" sentinels when reading wall distances.
5. As a player, I want non-ghost vehicles to appear in my laser scan, so that I can react to other racers around me.
6. As a player, I want ghost vehicles to be invisible to my laser scan, so that I don't waste avoidance logic on a car that can't collide with me.
7. As a player, I want my controller to keep internal state between ticks (one instance per vehicle), so that I can implement PID, filters, or planners.
8. As a player, I want to import numpy and math in my controller file, so that I can write efficient control code.
9. As a player, I want my car to reset to the nearest centerline point after a crash and pause for 0.5 s, so that crashes are recoverable and not catastrophically punishing.
10. As a player, I want my car to be a ghost for 1.5 s after the reset pause, so that I can't be rear-ended while I'm stationary at the reset point.
11. As a player, I want races to be lap-based with a configurable lap count, so that race length is my choice.
12. As a player, I want a time-trial mode where I am alone on the track, so that I can iterate on my controller without traffic.
13. As a player, I want a head-to-head mode against an AI baseline, so that I can measure my controller against a known skill level.
14. As a player, I want a head-to-head mode against another algorithm file, so that two approaches can be compared directly.
15. As a player, I want a multi-algorithm mode with N vehicles on the track at the same time, so that I can test my controller under traffic and collisions.
16. As a player, I want the start of the race to be a staggered grid behind the start/finish line with a countdown, so that the first corners are fair.
17. As a player, I want a live web view showing the track, car positions, headings, and driven paths, so that I can watch what my controller is actually doing.
18. As a player, I want a HUD in the web view (lap, speed, status racing/paused/ghost/finished/DNF, crash count, best and last lap), so that I can diagnose controller behavior while the race runs.
19. As a player, I want a results table after the race (finish order, total time, best lap, DNF reason), so that I know exactly how the race went.
20. As a player, I want a race timeout and a max-crash DNF limit, so that a broken controller can't hold the race hostage.
21. As a player, I want all game parameters (vehicle physics, control limits, sensor, race rules, baseline gains) in a single YAML file, so that I can tune the game without touching code.
22. As a player, I want the vehicle's control limits (max speed, max steering angle, steering rate, max acceleration) documented in the param file, so that I design my controller to the real physics instead of discovering the limits by crashing.
23. As a viewer, I want the track sent to the web view once as static data and vehicle state separately at a low rate, so that the page stays fast as vehicles or data rate grow.
24. As a viewer, I want a clean, self-describing data protocol, so that the appearance of the dashboard can be improved later without changing the sim.
25. As a developer, I want a deterministic headless race engine (no wall clock, no threads, no web) that runs a full race and returns results, so that I can test the entire game in CI.
26. As a developer, I want the wall-follow baseline to hold a target distance from a wall via a P/D controller, with all gains parameterized, so that I can tune its aggressiveness from the param file.
27. As a developer, I want the gap-follow baseline to steer toward the center of the widest forward gap, with speed scaled by gap width, so that it demonstrates a different, local-reactive driving style.
28. As a developer, I want both baselines to scale speed down with steering angle, so that they slow for corners and behave plausibly.
29. As a developer, I want the laser scan computed vectorized in numpy, so that N-vehicle races stay comfortably inside the 25 ms tick budget.
30. As a developer, I want the JAX dynamics batched into a single jit call for all vehicles, so that per-vehicle dispatch overhead doesn't add up.
31. As a developer, I want track construction to validate closure (turn angles sum to 360°, endpoints close), so that a malformed track fails loudly at build time instead of silently breaking lap counting.
32. As a developer, I want lap counting to require a mid-track checkpoint, so that a car cannot farm laps by oscillating over the start/finish line.
33. As a developer, I want a pure-pursuit reference controller, so that there is a strong benchmark every player controller can try to beat.
34. As a developer, I want a headless CLI flag to skip the web view, so that tests and CI runs don't need a browser or a network port.
35. As a developer, I want the simulation to be deterministic (same inputs, same trajectory), so that flaky race tests are debuggable.

## Implementation Decisions

- **Full restructure**: the existing experimental files are turned over and replaced by a package containing: a config loader, a track module, a dynamics module, a sensor module, a controller API module, a race engine, and a web module. A CLI entry point and a controllers folder sit beside it. No legacy behavior is preserved except the pure-pursuit algorithm, which is ported to the new controller API as a reference baseline.
- **One YAML param file** is the single source of truth, loaded into typed config objects. Sections: simulation (tick dt, physics substeps), vehicle (kinematic parameters and control limits: max/min speed, max acceleration, max/min steering angle, max steering rate), sensor (beam count), race (lap count, time limit, crash-pause duration, ghost duration, collision distance, max crashes before DNF), track (width, occupancy-grid resolution), baselines (one block per algorithm with every gain).
- **Controller contract**: a class with `reset(track_info)` and `step(state, scan) -> (speed, steering)`, where `state` is (x, y, yaw, speed, steering_angle) and `scan` is a numpy array of beam distances in radians-ordered 360° coverage with `np.inf` on no-hit. One instance per vehicle, so internal state is allowed. Controller files are loaded by dynamic import and the module must define exactly one concrete controller class. numpy and math imports are allowed; there is no sandboxing (local trust model). A stub file in the controllers folder is the player's starting point.
- **Physics**: kinematic single-track (bicycle) model following the CommonRoad convention, integrated with RK4 substeps inside the tick. Control inputs are target speed and target steering angle; the model applies acceleration, speed, steering-angle, and steering-rate constraints. The model is evaluated **batched over all vehicles in one jitted call** on an (N, 7) state array. JAX is warmed up before the race so first-tick compilation never slows the race.
- **Track module**: tracks are composed of straight and turn segments; construction validates closure (sum of turn angles ±360°, endpoint gap below epsilon). The centerline is resampled at fixed spacing and fit with cubic-spline Frenet coordinates (s, d, dyaw). Walls are an occupancy grid: a cell is occupied when it lies farther than half the track width from the centerline. Wall collision is a grid query against the vehicle footprint. The start/finish line plus one mid-track checkpoint gate lap counting. Three closed-loop tracks ship, ascending in difficulty (reworked from the old open-path levels).
- **Sensor**: 72 beams at 5° spacing, full 360°. Rays are sampled uniformly at grid resolution and vectorized in numpy (measured ~0.6 ms for 8 vehicles with short rays); first hit wins. Non-ghost vehicles contribute via closed-form ray-circle intersection with radius equal to the collision distance. Ghost vehicles are excluded entirely. No max range: rays run until first hit (on closed tracks every ray hits a wall within roughly one track width, so cost is bounded).
- **Crash flow**: on wall or vehicle contact, the car is placed at the nearest centerline pose (heading = centerline heading, speed = 0, steering = 0), then **paused 0.5 s** (zero outputs, controller not consulted), then **ghost 1.5 s** (excluded from collision checks and from all laser scans), then back to racing. Pause and ghost are sequential (2.0 s total). A per-vehicle crash counter drives the max-crash DNF.
- **Race engine**: one single-threaded fixed-step loop (40 Hz). Per tick, in order: each racing controller is stepped and given a fresh scan → commands are written → dynamics are integrated batched → collisions are checked (wall per vehicle, pairwise vehicle-vehicle) → crash handling (reset/pause/ghost timers) → lap bookkeeping. The engine is deterministic and runs headless; wall-clock pacing and the web view are a thin live-mode wrapper around it.
- **Race modes and rules**: time trial (single controller, fixed laps, best lap reported), head-to-head (two controllers), multi (N controllers). Multi/head-to-head start from a staggered grid behind the start/finish line after a countdown. The race continues until every vehicle has finished or the time limit expires; ranking is by finish time, DNFs last with reason (timeout or max crashes).
- **Baselines**: wall follow — pick the nearest wall in a forward sector, hold a target lateral distance via P/D on the heading error to an offset target point, speed = v_ref × (1 − k·|steering|) clamped. Gap follow — over a forward cone (±60°), find the widest gap between opposing wall hits, steer toward the gap midpoint at a fixed lookahead, speed = min(v_max, k_gap × gap_width) × (1 − k·|steering|). Pure pursuit — ported from the existing experiment, tracks the centerline with speed-scaled lookahead. Every gain, offset, cone angle, and speed factor is a parameter in the param file.
- **Web module**: FastAPI + WebSocket served in a thread beside the sim loop; the front end is one static HTML page with a plain-canvas renderer (vanilla JS, no framework, no build step). Protocol: on connect, one **static** message (centerline, occupancy grid as origin/resolution/occupied-cells, track width, start line); then a **dynamic** message every ~150 ms (sim time, phase, countdown, per-vehicle id/name/position/heading/speed/steering/lap/status/best lap/last lap/crash count/finish time). `null` in JSON stands for no-hit (np.inf in-process). The front end prerenders the track to an offscreen canvas once and only redraws cars and HUD per dynamic message — the protocol split is the seam that lets the appearance be improved later without touching the sim.
- **CLI**: subcommands `time-trial` and `race`, with options for track, controller file(s) (comma-separated), and lap count override; a headless flag disables the web view.
- **Dependencies**: add pyyaml, fastapi, uvicorn, pytest; drop pynput and matplotlib (teleop and matplotlib viz are removed).

## Testing Decisions

- **Primary seam — the headless race engine.** One entry point: run a race (or time trial) on a given track with given controller instances and race config, returning results (finish order, total times, best/last lap, crash counts, DNF reasons). This seam is deterministic — no wall clock, no threads, no web — and is where virtually everything is tested: crash → reset → pause → ghost behavior, lap counting with the checkpoint rule, all three race modes, timeout and max-crash DNF, baselines actually completing laps, and the tick-time budget.
- **Supporting seam — track construction.** Build a track from a segment spec, then query it: Frenet round-trip (to Frenet and back to Cartesian), wall-collision queries, checkpoint/start-line state. Needed so the engine is exercised on known geometry.
- **Controller loading** is tested through the engine's input path (file → instance → races), not as a separate seam.
- **Web protocol** is tested as a pure state → JSON serializer: assert the shape of the static message and of a dynamic message (including `null` for no-hit and all status values). No server or socket tests.
- **Dynamics and sensor get no dedicated unit tests.** They are internal to the engine and are covered by behavioral tests through the engine: a car driven straight at constant speed stays on a straight; a car pointed at a wall resets to the centerline; a ghost vehicle is absent from another vehicle's scan; a non-ghost vehicle appears in it.
- **Good test = external behavior only.** Tests assert results, statuses, and geometry — never implementation details (no JAX internals, no grid-index arithmetic, no ray-marching internals).
- **Prior art**: none — the repo contains no tests today (experiments only), so pytest is introduced fresh. The determinism of the headless engine is what makes the tests hermetic and repeatable.

## Out of Scope

- No sandboxing or resource limits on player controller code (local tool, trust model).
- No vehicle-to-vehicle contact physics beyond reset-on-contact (no pushing, no restitution).
- No networked multiplayer; everything runs locally via CLI.
- No 3D rendering, no mobile UI, no audio.
- No replay/recording of finished races; the web view is live-only.
- No track editor; tracks are authored in code/params.
- No anti-cheat beyond the trust model (player code runs in-process and could in principle read anything; that's accepted).
- No persistent leaderboard or cross-race statistics; results are per-run.

## Further Notes

- **Measured real-time budget at 8 vehicles per 25 ms tick** (numpy, this machine): vectorized laser scans 0.63 ms (rays ≤ 3 m) to 2.25 ms (rays ≤ 10 m); batched JAX dynamics ~0.3 ms; controllers (baselines) 1–4 ms; collisions/laps/web push < 0.3 ms. Total ~5–7 ms → 3–5× headroom. The first constraint to bite at larger N (≈20–30) is per-controller Python overhead, not the scan.
- **Beam count 72 (5° spacing)** is the chosen performance/resolution trade-off; it is a parameter, not a constant.
- **Baseline semantics follow the F1TENTH course kit**: wall follow is the PID corridor-following of Lab 3; gap follow is the reactive "follow the gap" obstacle avoidance of Lecture 5 / Lab 4.
- **Assumptions confirmed during planning**: pause (0.5 s) and ghost (1.5 s) are sequential (2.0 s total); default 3 laps; DNF after 5 crashes or a 300 s timeout (both parameters); grid start staggered behind the start/finish line; player files may import numpy/math with no sandbox.
- The old open-path levels are reworked into closed loops by the new track builder; the pure-pursuit experiment is the seed for the reference baseline.
- The web protocol's static/dynamic split is the deliberate scaling seam: "if we scale we only need to improve the appearance."
