"""Starter controller: copy this file to ``controllers/my_car.py`` and edit it.

This file is a working skeleton that documents the whole contract a
controller must honour, plus a tiny laser-based driver that survives the
stadium so you can see a car moving before you change anything.

HOW THE ENGINE DRIVES YOUR CODE
-------------------------------
Your file is loaded once and must define exactly one concrete subclass of
``Controller``. The engine builds one instance per vehicle and calls:

  * ``reset(track_info)``  -- once, before the first tick. ``track_info`` is a
    frozen ``TrackInfo`` with the track name, length, width, start pose, and the
    full ``centerline`` (a tuple of ``(x, y)`` points). Store anything you want
    to remember on ``self`` here.
  * ``step(x, y, yaw, speed, steering_angle, laser_scan)`` -- once per tick,
    40 times a second, for the life of the vehicle (racing and ghosting). It
    returns ``(target_speed, target_steering_angle)``.

One instance serves one vehicle, so any state you keep on ``self`` persists
between ticks -- use it for filters, memory, lap bookkeeping, whatever.

THE STATE THE ENGINE HANDS YOU
------------------------------
Every ``step`` call gives you the vehicle's current state:

  * ``x, y``        position on the track plane, metres.
  * ``yaw``         heading, radians, 0 = +x, increasing counter-clockwise.
  * ``speed``       scalar speed along the heading, m/s (>= 0).
  * ``steering_angle`` current front-wheel steering, radians (+ = left).

THE LASER SCAN
--------------
``laser_scan`` is a numpy array of beam distances in metres, one per beam,
covering the full circle. There are ``beam_count`` beams (72 by default):

  * beam 0 points straight ahead (along ``yaw``);
  * beam ``i`` is at ``yaw + i * 360 / beam_count`` degrees, going
    counter-clockwise, so beams 1..35 sweep the left side and 36..71 the
    right;
  * a beam stops at the first thing it hits -- a wall, or another *racing*
    vehicle's collision circle -- and reads ``np.inf`` when it hits nothing.
    There is no max range, so always guard with ``math.isfinite``.

YOUR OUTPUTS
------------
Return ``(target_speed, target_steering)``. The vehicle chases both of them but
is limited by the hardware, so commanding more does not help:

  * ``target_speed`` in m/s, clamped to ``[min_speed, max_speed]`` and limited
    by ``max_accel``;
  * ``target_steering`` in radians, clamped to ``[min_steer, max_steer]`` and
    limited by ``max_steer_rate``.

The current limits live in the ``vehicle:`` block of the param file
(``params/default.yaml`` by default): ``max_speed: 25.0``, ``max_accel: 8.0``,
``max_steer: 0.5``. Keep your commands inside those numbers.

ALLOWED IMPORTS
---------------
Your file is imported as its own module. Use the standard library and numpy
freely; import the base class from ``cocoracer.controller``. You do not need to
import anything else from the engine -- everything you need arrives as
arguments to ``reset`` and ``step``.
"""

import math

import numpy as np

from cocoracer.controller import Controller, TrackInfo


class MyCar(Controller):
    """Drive forward, keeping centered between the two walls.

    A deliberately small driver: it holds a fixed cruise speed and steers to
    stay midway between the nearest left and nearest right wall. The middle of
    the track is the centerline, so this follows the straights *and* the
    hairpins using the laser alone -- no centerline needed. Replace ``step``
    with your own logic; keep the signature and the ``(speed, steering)``
    return.
    """

    # Tuning knobs -- edit freely. Both stay inside the vehicle limits.
    CRUISE_SPEED = 12.0  # m/s (limit 25.0)
    MAX_STEER = 0.45  # rad (limit 0.5)
    WATCH_BEAMS = 14  # watch 70 deg either side of straight ahead
    CENTER_GAIN = 5.0  # m of off-center that commands full lock
    SLOW_DOWN_AT = 30.0  # m: start easing off when a wall is this close ahead

    def reset(self, track_info: TrackInfo) -> None:
        # Initialize any internal state here, once before the first tick.
        # ``track_info.centerline`` is available if you want to drive from it.
        self._name = track_info.name

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
        n = len(scan)
        half = min(self.WATCH_BEAMS, n // 2 - 1)

        # Nearest wall on each side, excluding straight ahead (beam 0).
        d_left = float(np.min(scan[1 : half + 1]))
        d_right = float(np.min(scan[n - half : n]))

        if math.isfinite(d_left) and math.isfinite(d_right):
            # Off-center by (d_right - d_left) / 2: positive means the car has
            # drifted toward the left wall. Steer the other way to recenter.
            off_center = (d_right - d_left) / 2.0
            steer = -self.MAX_STEER * float(
                np.clip(off_center / self.CENTER_GAIN, -1.0, 1.0)
            )
        elif math.isfinite(d_left):
            steer = -self.MAX_STEER  # only a left wall: steer right
        elif math.isfinite(d_right):
            steer = self.MAX_STEER  # only a right wall: steer left
        else:
            steer = 0.0

        # Ease off when a wall is close straight ahead.
        target_speed = self.CRUISE_SPEED
        d_ahead = float(scan[0])
        if math.isfinite(d_ahead) and d_ahead < self.SLOW_DOWN_AT:
            target_speed = (
                self.CRUISE_SPEED * max(0.0, d_ahead - 8.0) / (self.SLOW_DOWN_AT - 8.0)
            )
        return float(target_speed), steer
