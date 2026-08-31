# cocoracer

Program your own autonomous racing controller and race it against baselines in a deterministic 2-D car.

You write a Python controller that reads a 360° laser scan and returns a target speed and a steering angle. cocoracer runs it 40 times a second against a physical car model, on a wall grid, against other cars it can clip. Run it headless for lap times, or watch it live in a browser.

## Install

Python 3.10+ (developed on 3.12).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The `.[dev]` extra adds pytest, ruff, and mypy on top of the runtime stack (numpy, jax, scipy, and the FastAPI/uvicorn web view). Drop it if you only want to race. Installing puts the `cocoracer` command on PATH; `python -m cocoracer.cli` works too.

## Quickstart

```bash
# 1. Copy the starter controller and make it yours.
cp controllers/starter.py controllers/my_car.py
```

Open `controllers/my_car.py` and edit `step`. The whole contract — state fields, the laser scan, the outputs, what you may import — is documented in that file's docstring. As written, the starter finishes the stadium clean, so if you see laps flying you're set up right.

```bash
# 2. Time it alone (headless).
cocoracer time-trial --controller controllers/my_car.py --no-web

# 3. Race it against a baseline.
cocoracer race --controller controllers/my_car.py,controllers/pure_pursuit.py

# 4. Watch it live: drop --no-web and open the printed URL.
cocoracer race --controller controllers/my_car.py,controllers/pure_pursuit.py
# web view: http://127.0.0.1:8000
```

## The two commands

- `time-trial` — one controller alone; prints its lap times.
- `race` — two or more controllers head-to-head; prints the classified results. An N-vehicle race just adds more comma-separated controllers.

Both take the same options:

| flag | meaning |
| --- | --- |
| `--track NAME` | `icra-2023-short` (default), `right-interior`, `icra-2025`, `stadium` |
| `--controller PATH[,PATH...]` | controller files to load |
| `--laps N` | override the lap count |
| `--no-web` | run headless — no browser, just the results |
| `--port N` | web view port (ignored with `--no-web`, default 8000) |

`--params FILE` comes before the subcommand and points at a different param file. `cocoracer --help` and `cocoracer <command> --help` print the full list.

## The tick contract

Every tick (40 Hz) `step` gets the car's state `(x, y, yaw, speed, steering_angle)` and a 360° laser scan — 72 beams, one per 5°, `np.inf` when a beam hits nothing — and returns `(target_speed, target_steering_angle)`. The car chases both but is limited by the hardware in the `vehicle:` block of `params/default.yaml`: max speed 25 m/s, max accel 8 m/s², steer ±0.5 rad. `reset(track_info)` is called once before the first tick, and `track_info` carries the centerline if you want to drive from it. `controllers/starter.py` walks through all of this.

## Baselines

Three reference controllers ship in `controllers/`:

- `pure_pursuit.py` — follows the track centerline. The pace setter, about 1.6 s a lap on the stadium.
- `wall_follow.py` — reactive, laser only: holds a fixed gap from the nearest wall with a proportional-plus-damping term. No centerline, no track knowledge.
- `disparity_extender.py` — reactive, laser only: steers to equalize left and right wall distance and manages speed for how the track curves. No centerline.

The last two use only the laser scan — the same sensor your controller gets — so they're fair opponents and a starting point for reactive driving.

## Crashes, pauses, ghosts

Touching a wall (your footprint meets the grid) or clipping another *racing* car within 0.5 m is a crash. The car is reset to the nearest centerline pose with speed and steering zeroed, then:

1. **Paused** for 2 s — sits stopped, immune to collisions.
2. **Ghost** for 1.5 s — still being driven, but immune to collisions.
3. Back to **racing** — vulnerable again.

Five crashes ends the car (DNF, max crashes). So does 300 s on the clock (DNF, timeout). A crash costs a few seconds and some track position, but the car keeps going.

## Adding a track

Tracks live in the `tracks:` block of the param file. Two ways to add one.

Inline, as `segments` — straight and turn pieces, like the stadium:

```yaml
tracks:
  my_oval:
    width: 1.0
    resolution: 0.05
    segments:
      - { type: straight, length: 8.0 }
      - { type: turn, radius: 3.0, angle: 180.0 }
      - { type: straight, length: 8.0 }
      - { type: turn, radius: 3.0, angle: 180.0 }
```

Or from a JSON centerline in `params/tracks/`:

```yaml
tracks:
  my_circuit:
    file: tracks/my_circuit.json
```

where `my_circuit.json` is `{"width": 1.0, "resolution": 0.1, "centerline": [[x, y], ...]}`. The path is relative to the param file. The centerline must close (last point back near the first), must not self-intersect, and must stay wider than `width`.

The three shipped maps — `right-interior`, `icra-2023-short`, `icra-2025` — are built from PGM images; see `docs/adr/0003-pgm-track-import.md`.

Race on the new track with `--track my_oval`.

## Tests

```bash
ruff format .
ruff check .
mypy cocoracer tests
pytest
```

All four must come back clean.

## Layout

- `cocoracer/` — the engine: config, track building, vehicle dynamics, the laser sensor, collision, lap tracking, race state, the CLI, and the web view.
- `controllers/` — the baselines and the `starter.py` template.
- `params/` — `default.yaml` and the per-map track parameters.
- `tests/` — the test suite.
- `docs/` — coding style and ADRs.
