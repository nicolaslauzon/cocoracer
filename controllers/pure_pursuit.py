"""Pure-pursuit reference baseline.

Centerline following with a speed-scaled lookahead, ported from the
pre-package experiment to the controller API. The lookahead target is
the centerline point one lookahead distance ahead in arc length, and the
steering command is the classic pure-pursuit formula. Every parameter comes
from the param file's baselines.pure_pursuit block, injected at load
time.
"""

import math

import numpy as np

from cocoracer.controller import Controller, ControllerError, TrackInfo

_PARAMETERS = (
    "wheelbase",
    "max_steer",
    "lookahead_slope",
    "lookahead_offset",
    "min_lookahead",
    "max_lookahead",
    "target_speed",
)


class PurePursuit(Controller):
    def __init__(self, baselines: dict[str, dict]) -> None:
        block = baselines.get("pure_pursuit")
        if block is None:
            raise ControllerError(
                "param file is missing the baselines.pure_pursuit block"
            )
        parameters: dict[str, float] = {}
        for key in _PARAMETERS:
            if key not in block:
                raise ControllerError(f"baselines.pure_pursuit is missing key '{key}'")
            parameters[key] = float(block[key])
        self._wheelbase = parameters["wheelbase"]
        self._max_steer = parameters["max_steer"]
        self._slope = parameters["lookahead_slope"]
        self._offset = parameters["lookahead_offset"]
        self._min_lookahead = parameters["min_lookahead"]
        self._max_lookahead = parameters["max_lookahead"]
        self._target_speed = parameters["target_speed"]
        self._points: np.ndarray | None = None
        self._spacing = 0.0

    def reset(self, track_info: TrackInfo) -> None:
        if len(track_info.centerline) < 2:
            raise ControllerError(
                "pure pursuit needs the track centerline, but TrackInfo carries none"
            )
        self._points = np.asarray(track_info.centerline[:-1], dtype=np.float64)
        self._spacing = track_info.track_length / len(self._points)

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        if self._points is None:
            return 0.0, 0.0
        lookahead = min(
            max(speed * self._slope + self._offset, self._min_lookahead),
            self._max_lookahead,
        )
        dxs = self._points[:, 0] - x
        dys = self._points[:, 1] - y
        nearest = int(np.argmin(dxs * dxs + dys * dys))
        target = (nearest + int(math.ceil(lookahead / self._spacing))) % len(
            self._points
        )
        gx, gy = (float(v) for v in self._points[target])
        dx, dy = gx - x, gy - y
        chord = math.hypot(dx, dy)
        y_local = -dx * math.sin(yaw) + dy * math.cos(yaw)
        if chord > 1e-5:
            steer = math.atan(2.0 * self._wheelbase * y_local / chord**2)
        else:
            steer = 0.0
        steer = float(np.clip(steer, -self._max_steer, self._max_steer))
        return self._target_speed, steer
