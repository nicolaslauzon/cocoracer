"""Wall-follow baseline, F1TENTH Lab 3 semantics.

Reactive, laser-only: scan a forward sector, take the nearest hit, and
hold `target_wall_distance` from that wall with a P/D controller on the
heading error to the aim point (the hit, offset toward the track by the
target gap). Speed is v_ref scaled down by |steering|, clamped to
[0, v_ref]. No centerline is used. Every gain comes from the param
file's baselines.wall_follow block, injected at load time.
"""

import math

import numpy as np

from cocoracer.controller import Controller, ControllerError, TrackInfo

_GAINS = (
    "target_wall_distance",
    "kp",
    "kd",
    "v_ref",
    "steer_speed_factor",
    "sector_half_angle",
)

_BEAM_ANGLE = 2.0 * math.pi / 72.0
_TICK_DT = 1.0 / 40.0
_MAX_STEER = 0.5


class WallFollow(Controller):
    def __init__(self, baselines: dict[str, dict]) -> None:
        block = baselines.get("wall_follow")
        if block is None:
            raise ControllerError(
                "param file is missing the baselines.wall_follow block"
            )
        gains: dict[str, float] = {}
        for key in _GAINS:
            if key not in block:
                raise ControllerError(f"baselines.wall_follow is missing key '{key}'")
            gains[key] = float(block[key])
        self._gap = gains["target_wall_distance"]
        self._kp = gains["kp"]
        self._kd = gains["kd"]
        self._v_ref = gains["v_ref"]
        self._speed_factor = gains["steer_speed_factor"]
        self._half_beams = max(
            1, int(round(gains["sector_half_angle"] / math.degrees(_BEAM_ANGLE)))
        )
        self._prev_error = 0.0

    def reset(self, track_info: TrackInfo) -> None:
        self._prev_error = 0.0

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        scan = np.asarray(laser_scan, dtype=np.float64)
        half = self._half_beams
        n = len(scan)
        sector_idx = np.concatenate([np.arange(half + 1), np.arange(n - half, n)])
        sector = scan[sector_idx]
        k = int(np.argmin(sector))
        if not math.isfinite(float(sector[k])):
            return 0.0, 0.0
        beam = int(sector_idx[k])
        distance = float(sector[k])
        theta = beam * _BEAM_ANGLE
        if theta > math.pi:
            theta -= 2.0 * math.pi
        hit_y = distance * math.sin(theta)
        if 0 < beam <= half:
            aim_y = hit_y - self._gap
        else:
            aim_y = hit_y + self._gap
        error = math.atan2(aim_y, distance * math.cos(theta))
        delta = math.atan2(
            math.sin(error - self._prev_error),
            math.cos(error - self._prev_error),
        )
        self._prev_error = error
        steer = self._kp * error + self._kd * delta / _TICK_DT
        steer = float(np.clip(steer, -_MAX_STEER, _MAX_STEER))
        target_speed = self._v_ref * (1.0 - self._speed_factor * abs(steer))
        return float(np.clip(target_speed, 0.0, self._v_ref)), steer
