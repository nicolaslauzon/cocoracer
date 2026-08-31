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
