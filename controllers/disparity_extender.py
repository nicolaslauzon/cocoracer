"""Disparity-extender reactive baseline.

Reactive, laser-only: no centerline. The full-circle scan is split into a
front sector (-90..+90 degrees) and the rest. Where two adjacent front
beams disagree by more than `disparity_threshold` there is an edge; the
nearer side of that edge is extended across the car's width so the car
does not aim a gap it cannot physically fit through. The target is the
farthest beam of the extended front sector, and the car steers toward it
with a P/D law on the target angle. Speed comes from the distance to the
target (full speed when far, a flat brake zone when close, linear in
between) and is additionally capped by the friction-limited speed for the
current steering angle. Every parameter comes from the param file's
baselines.disparity_extender block, injected at load time.
"""

import math

import numpy as np

from cocoracer.controller import Controller, ControllerError, TrackInfo

_PARAMETERS = (
    "car_width",
    "wheelbase",
    "max_steer",
    "kp",
    "kd",
    "full_speed_distance",
    "brake_distance",
    "min_speed",
    "max_speed",
    "friction",
    "disparity_threshold",
)
_GRAVITY = 9.81998


class DisparityExtender(Controller):
    def __init__(self, baselines: dict[str, dict]) -> None:
        block = baselines.get("disparity_extender")
        if block is None:
            raise ControllerError(
                "param file is missing the baselines.disparity_extender block"
            )
        parameters: dict[str, float] = {}
        for key in _PARAMETERS:
            if key not in block:
                raise ControllerError(
                    f"baselines.disparity_extender is missing key '{key}'"
                )
            parameters[key] = float(block[key])
        self._car_width = parameters["car_width"]
        self._wheelbase = parameters["wheelbase"]
        self._max_steer = parameters["max_steer"]
        self._kp = parameters["kp"]
        self._kd = parameters["kd"]
        self._full_speed_distance = parameters["full_speed_distance"]
        self._brake_distance = parameters["brake_distance"]
        self._min_speed = parameters["min_speed"]
        self._max_speed = parameters["max_speed"]
        self._friction = parameters["friction"]
        self._disparity_threshold = parameters["disparity_threshold"]
        self._last_angle = 0.0

    def reset(self, track_info: TrackInfo) -> None:
        self._last_angle = 0.0

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
        front, angles = _front_sector(scan)
        beam_step = 2.0 * math.pi / len(scan)
        extended = _extend_disparities(
            front, self._disparity_threshold, self._car_width, beam_step
        )
        target_index = _find_max_gap(extended)
        target_angle = float(angles[target_index])
        steering = self._kp * target_angle + self._kd * (
            target_angle - self._last_angle
        )
        self._last_angle = target_angle
        steering = float(np.clip(steering, -self._max_steer, self._max_steer))
        target_distance = float(extended[target_index])
        if not math.isfinite(target_distance):
            return self._min_speed, 0.0
        base = _speed_for_distance(
            target_distance,
            self._full_speed_distance,
            self._brake_distance,
            self._min_speed,
            self._max_speed,
        )
        final = _limit_speed_when_turning(
            steering,
            base,
            self._wheelbase,
            self._max_steer,
            self._friction,
            self._min_speed,
            self._max_speed,
        )
        return final, steering


def _front_sector(scan: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The front half of the scan: beams from -90 to +90 degrees (inclusive).

    Returns a copy of those range values and their signed angles in
    radians (counter-clockwise positive, 0 = straight ahead).
    """
    n = len(scan)
    beam_step = 2.0 * math.pi / n
    start = int(round((-math.pi / 2.0) / beam_step)) % n
    count = int(round(math.pi / beam_step)) + 1
    idx = (start + np.arange(count)) % n
    angles = idx * beam_step
    angles = np.where(angles > math.pi, angles - 2.0 * math.pi, angles)
    return scan[idx].copy(), angles


def _extend_disparities(
    ranges: np.ndarray, threshold: float, car_width: float, angle_step: float
) -> np.ndarray:
    """Extend each edge so it spans the car's width.

    An edge is a pair of adjacent beams whose ranges differ by at least
    `threshold`. The nearer beam of the pair is propagated outward over
    the arc that the car's width subtends at that range, clamping those
    beams to the nearer value (never pushing them farther).
    """
    n = len(ranges)
    edges = [
        i
        for i in range(n - 1)
        if math.isfinite(ranges[i])
        and math.isfinite(ranges[i + 1])
        and abs(ranges[i] - ranges[i + 1]) >= threshold
    ]
    out = ranges.copy()
    for i in edges:
        near = min(out[i], out[i + 1])
        if near <= 0.0 or not math.isfinite(near):
            continue
        samples = int(math.ceil(car_width / (angle_step * near)))
        if out[i] < out[i + 1]:
            lo, hi = i + 1, min(i + 1 + samples, n)
        else:
            lo, hi = max(0, i - samples + 1), i + 1
        for j in range(lo, hi):
            out[j] = min(near, out[j])
    return out


def _find_max_gap(ranges: np.ndarray) -> int:
    """Index of the farthest beam; on a tie, the middle one."""
    best = -1.0
    ties: list[int] = []
    for i, value in enumerate(ranges):
        effective = value if math.isfinite(value) else math.inf
        if effective > best:
            best = effective
            ties = [i]
        elif effective == best:
            ties.append(i)
    return ties[len(ties) // 2]


def _speed_for_distance(
    distance: float,
    full_speed_distance: float,
    brake_distance: float,
    min_speed: float,
    max_speed: float,
) -> float:
    """Full speed when the target is far, a flat ramp to a stop when close."""
    if distance >= full_speed_distance:
        return max_speed
    if distance <= brake_distance:
        return min_speed * (distance / brake_distance)
    slope = (max_speed - min_speed) / (full_speed_distance - brake_distance)
    return slope * (distance - brake_distance) + min_speed


def _limit_speed_when_turning(
    steering: float,
    speed: float,
    wheelbase: float,
    max_steer: float,
    friction: float,
    min_speed: float,
    max_speed: float,
) -> float:
    """Cap the speed by the friction limit for the commanded steering angle.

    The cap is blended in with a sigmoid on |steering|/max_steer so that
    at small angles the distance-based speed dominates and at large
    angles the physics limit (sqrt(friction * g * turning radius)) takes
    over.
    """
    angle = abs(steering)
    turning_radius = wheelbase / max(math.sin(angle), 1e-6)
    theoretical = math.sqrt(friction * _GRAVITY * turning_radius)
    sigmoid = 1.0 / (1.0 + math.exp(-10.0 * (angle / max_steer - 0.5)))
    adjusted = (1.0 - sigmoid) * speed + sigmoid * theoretical
    capped = min(speed, adjusted)
    return float(np.clip(capped, min_speed, max_speed))
