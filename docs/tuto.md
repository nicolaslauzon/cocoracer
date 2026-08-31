# cocoracer demo

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/nicolaslauzon/cocoracer.git
```

## What you got

Save this as `stub.py` in your working directory:

```python
import numpy as np

from cocoracer.controller import Controller, TrackInfo


class MyCar(Controller):
    SPEED = 20.0

    def reset(self, track_info: TrackInfo) -> None:
        pass

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        return self.SPEED, 0.0
```

It drives forward at 20 m/s, ignores the laser, hits a wall, and DNFs.
Your job: edit `step()` so it actually drives.

## How step() works

The engine calls `step()` 40 times a second. You return two numbers:

- **target_speed** in m/s (max 25)
- **target_steering_angle** in radians (max 0.5, positive = left)

The car chases your targets but respects hardware limits: 25 m/s top speed,
8 m/s² acceleration, ±0.5 rad steering.

## What you get each tick

**State:**

- `x, y` — position in metres
- `yaw` — heading in radians (0 = +x direction, counter-clockwise positive)
- `speed` — scalar speed along heading, m/s
- `steering_angle` — current front-wheel angle, radians

**Laser scan:**

- 72 beams covering the full circle
- Beam 0 points straight ahead (along yaw)
- Beam `i` is at `yaw + i * 5°` counter-clockwise
- `np.inf` means the beam hit nothing
- Use `math.isfinite()` to check if a beam hit a wall

**TrackInfo** (passed to `reset()`, once before the first tick):

- `name` — track name
- `track_length` — total lap distance in metres
- `width` — track width in metres
- `start_x`, `start_y`, `start_yaw` — starting pose
- `centerline` — tuple of `(x, y)` points along the track spine

## Try it

Time trial (alone):

```bash
demo time-trial stub.py
```

Head-to-head against the wall follower:

```bash
demo race stub.py
```

Both open a browser at http://127.0.0.1:8000 where you can watch the cars
race in real time. Edit `stub.py`, rerun, and watch your lap times change.
