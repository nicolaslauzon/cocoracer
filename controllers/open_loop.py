"""Trivial stub controller: drives forward at a constant speed.

It ignores the track entirely, so it plows into the first wall, gets
reset, and repeats until it burns through the crash budget and DNFs.
Its job is to keep the headless engine exercisable end to end.
"""

from cocoracer.controller import Controller, TrackInfo


class OpenLoop(Controller):
    SPEED = 2.0

    def reset(self, track_info: TrackInfo) -> None:
        pass

    def step(
        self, x: float, y: float, yaw: float, speed: float, steering_angle: float
    ) -> tuple[float, float]:
        return self.SPEED, 0.0
