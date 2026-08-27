import numpy as np
from custom_types import Pose

from scipy.interpolate import CubicSpline


class FrenetConverter:

    def __init__(self, centerline: list[Pose]):
        self.waypoints_x = np.array([p.x_m for p in centerline])
        self.waypoints_y = np.array([p.y_m for p in centerline])
        self.waypoints_psi = np.array([p.heading_rad for p in centerline])

        self.waypoints_s = None
        self.spline_x = None
        self.spline_y = None
        self.raceline_length = None
        self.iter_max = 3

        self.build_raceline()

    def build_raceline(self):
        dx = np.diff(self.waypoints_x)
        dy = np.diff(self.waypoints_y)
        distances = np.sqrt(dx**2 + dy**2)

        self.waypoints_s = np.zeros_like(self.waypoints_x)
        self.waypoints_s[1:] = np.cumsum(distances)

        self.spline_x = CubicSpline(self.waypoints_s, self.waypoints_x)
        self.spline_y = CubicSpline(self.waypoints_s, self.waypoints_y)
        self.raceline_length = float(self.waypoints_s[-1])

    def get_approx_s(self, x: float, y: float) -> float:
        dists_sq = (self.waypoints_x - x) ** 2 + (self.waypoints_y - y) ** 2
        idx = np.argmin(dists_sq)
        return float(self.waypoints_s[idx])

    def get_frenet(self, x: float, y: float, yaw: float) -> tuple:
        s_approx = self.get_approx_s(x, y)
        s, d = self.get_frenet_coord(x, y, s_approx)

        dx = float(self.spline_x(s, 1))
        dy = float(self.spline_y(s, 1))
        track_yaw = np.arctan2(dy, dx)

        dyaw = yaw - track_yaw
        dyaw = (dyaw + np.pi) % (2 * np.pi) - np.pi
        return s, d, dyaw

    def get_frenet_coord(
        self, x: float, y: float, s_start: float
    ) -> tuple[float, float]:
        s = s_start
        d = 0.0
        max_step = self.raceline_length / len(self.waypoints_s)

        for _ in range(self.iter_max):
            proj, current_d = self.check_perpendicular(x, y, s)
            d = current_d

            if abs(proj) < 1e-4:
                break

            delta_s = np.clip(proj, -max_step, max_step)
            s = (s + delta_s) % self.raceline_length

        return s, d

    def check_perpendicular(self, x: float, y: float, s: float) -> tuple[float, float]:
        dx_ds = float(self.spline_x(s, 1))
        dy_ds = float(self.spline_y(s, 1))

        tangent_norm = np.hypot(dx_ds, dy_ds)
        if tangent_norm == 0:
            tangent_norm = 1e-6

        tx = dx_ds / tangent_norm
        ty = dy_ds / tangent_norm

        x_vec = x - float(self.spline_x(s))
        y_vec = y - float(self.spline_y(s))

        proj = tx * x_vec + ty * y_vec
        d = (-ty) * x_vec + tx * y_vec

        return proj, d

    def get_cartesian(self, s: float, d: float) -> tuple[float, float, float]:
        s = s % self.raceline_length

        x_spline = float(self.spline_x(s))
        y_spline = float(self.spline_y(s))

        dx = float(self.spline_x(s, 1))
        dy = float(self.spline_y(s, 1))
        psi = np.arctan2(dy, dx)

        x = x_spline + d * np.cos(psi + np.pi / 2)
        y = y_spline + d * np.sin(psi + np.pi / 2)

        return x, y, psi
