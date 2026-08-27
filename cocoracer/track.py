import math

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

from cocoracer.config import TrackSpec


class TrackError(ValueError):
    pass


def wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


class Track:
    def __init__(
        self,
        name: str,
        half_width: float,
        resolution: float,
        track_length: float,
        centerline: np.ndarray,
        spline_x: CubicSpline,
        spline_y: CubicSpline,
        grid_origin: tuple[float, float],
        grid_shape: tuple[int, int],
        occupied: np.ndarray,
        frenet_tree: cKDTree,
        frenet_s: np.ndarray,
    ) -> None:
        self.name = name
        self.half_width = half_width
        self.resolution = resolution
        self.track_length = track_length
        self.centerline = centerline
        self.spline_x = spline_x
        self.spline_y = spline_y
        self.grid_origin = grid_origin
        self.grid_shape = grid_shape
        self.occupied = occupied
        self._frenet_tree = frenet_tree
        self._frenet_s = frenet_s

    @property
    def centerline_xy(self) -> np.ndarray:
        return self.centerline[:, :2]

    @property
    def start_pose(self) -> tuple[float, float, float]:
        x, y, yaw = self.centerline[0]
        return float(x), float(y), float(yaw)

    @property
    def checkpoint_s(self) -> float:
        return self.track_length / 2.0

    def to_cartesian(self, s: float, d: float) -> tuple[float, float, float]:
        s = s % self.track_length
        x_c = float(self.spline_x(s))
        y_c = float(self.spline_y(s))
        dx = float(self.spline_x(s, 1))
        dy = float(self.spline_y(s, 1))
        psi = math.atan2(dy, dx)
        nx = math.cos(psi + math.pi / 2)
        ny = math.sin(psi + math.pi / 2)
        return x_c + d * nx, y_c + d * ny, psi

    def to_frenet(self, x: float, y: float, yaw: float) -> tuple[float, float, float]:
        s, d = self._refine_frenet(x, y, self._approx_s(x, y))
        dx = float(self.spline_x(s, 1))
        dy = float(self.spline_y(s, 1))
        psi = math.atan2(dy, dx)
        return s, d, wrap_angle(yaw - psi)

    def _approx_s(self, x: float, y: float) -> float:
        _, idx = self._frenet_tree.query((x, y))
        return float(self._frenet_s[int(idx)])

    def _refine_frenet(self, x: float, y: float, s0: float) -> tuple[float, float]:
        s = s0
        d = 0.0
        max_step = self.track_length / len(self._frenet_s)
        for _ in range(3):
            proj, d = self._perpendicular(x, y, s)
            if abs(proj) < 1e-4:
                break
            s = (s + float(np.clip(proj, -max_step, max_step))) % self.track_length
        return s, d

    def _perpendicular(self, x: float, y: float, s: float) -> tuple[float, float]:
        dx_ds = float(self.spline_x(s, 1))
        dy_ds = float(self.spline_y(s, 1))
        norm = math.hypot(dx_ds, dy_ds) or 1e-6
        tx, ty = dx_ds / norm, dy_ds / norm
        x_vec = x - float(self.spline_x(s))
        y_vec = y - float(self.spline_y(s))
        proj = tx * x_vec + ty * y_vec
        d = -ty * x_vec + tx * y_vec
        return proj, d

    def nearest_centerline(self, x: float, y: float) -> tuple[float, float, float]:
        dists = (self.centerline_xy[:, 0] - x) ** 2 + (
            self.centerline_xy[:, 1] - y
        ) ** 2
        idx = int(np.argmin(dists))
        cx, cy, cyaw = self.centerline[idx]
        return float(cx), float(cy), float(cyaw)

    def point_in_wall(self, x: float, y: float) -> bool:
        ox, oy = self.grid_origin
        ix = int(math.floor((x - ox) / self.resolution))
        iy = int(math.floor((y - oy) / self.resolution))
        ny, nx = self.grid_shape
        if ix < 0 or iy < 0 or ix >= nx or iy >= ny:
            return True
        return bool(self.occupied[iy, ix])

    def footprint_in_wall(
        self, x: float, y: float, yaw: float, length: float, width: float
    ) -> bool:
        return any(
            self.point_in_wall(px, py)
            for px, py in _footprint_points(x, y, yaw, length, width, self.resolution)
        )


def _generate_centerline(segments: list) -> np.ndarray:
    x = y = yaw = 0.0
    points: list[list[float]] = [[x, y, yaw]]
    for seg in segments:
        if seg.type == "straight":
            points.extend(_straight_points(x, y, yaw, seg.length))
        else:
            points.extend(_turn_points(x, y, yaw, seg.radius, seg.angle))
        x, y, yaw = points[-1]
    return np.asarray(points, dtype=np.float64)


def _straight_points(
    x: float, y: float, yaw: float, length: float
) -> list[list[float]]:
    n = max(1, int(math.ceil(length / 0.1)))
    step = length / n
    pts: list[list[float]] = []
    for _ in range(n):
        x += math.cos(yaw) * step
        y += math.sin(yaw) * step
        pts.append([x, y, yaw])
    return pts


def _turn_points(
    x: float, y: float, yaw: float, radius: float, angle_deg: float
) -> list[list[float]]:
    theta = math.radians(angle_deg)
    sign = 1.0 if theta >= 0 else -1.0
    yaw0 = yaw
    cx = x + radius * sign * math.cos(yaw0 + math.pi / 2)
    cy = y + radius * sign * math.sin(yaw0 + math.pi / 2)
    base = yaw0 - sign * math.pi / 2
    n = max(1, int(math.ceil(abs(angle_deg) / 2.0)))
    pts: list[list[float]] = []
    for i in range(1, n + 1):
        phi = theta * i / n
        px = cx + radius * math.cos(base + phi)
        py = cy + radius * math.sin(base + phi)
        pts.append([px, py, yaw0 + phi])
    return pts


def _validate_closure(raw: np.ndarray, spec: TrackSpec) -> None:
    turn_sum = sum(seg.angle for seg in spec.segments if seg.type == "turn")
    if abs(abs(turn_sum) - 360.0) > 0.01:
        raise TrackError(
            f"track {spec.name!r} turn angles sum to {turn_sum:.3f} deg, expected +/-360"
        )
    gap = math.hypot(raw[-1, 0] - raw[0, 0], raw[-1, 1] - raw[0, 1])
    if gap > 0.05:
        raise TrackError(
            f"track {spec.name!r} does not close: endpoint gap {gap:.4f} m"
        )


def _resample_and_fit(raw: np.ndarray, spacing: float) -> tuple:
    dx = np.diff(raw[:, 0])
    dy = np.diff(raw[:, 1])
    seg_len = np.hypot(dx, dy)
    s_cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    track_length = float(s_cum[-1])
    n = max(3, int(math.ceil(track_length / spacing)))
    s_sample = np.linspace(0.0, track_length, n, endpoint=True)
    x_sample = np.interp(s_sample, s_cum, raw[:, 0])
    y_sample = np.interp(s_sample, s_cum, raw[:, 1])
    yaw_sample = np.interp(s_sample, s_cum, raw[:, 2])
    x_sample[-1] = x_sample[0]
    y_sample[-1] = y_sample[0]
    yaw_sample[-1] = yaw_sample[0]
    spline_x = CubicSpline(s_sample, x_sample, bc_type="periodic")
    spline_y = CubicSpline(s_sample, y_sample, bc_type="periodic")
    centerline = np.column_stack(
        [x_sample, y_sample, np.array([wrap_angle(a) for a in yaw_sample])]
    )
    tree = cKDTree(np.column_stack([x_sample[:-1], y_sample[:-1]]))
    return centerline, track_length, spline_x, spline_y, tree, s_sample[:-1]


def _build_grid(
    centerline: np.ndarray, spec: TrackSpec
) -> tuple[tuple[float, float], tuple[int, int], np.ndarray]:
    half_width = spec.width / 2.0
    margin = half_width + 0.5
    xs = centerline[:, 0]
    ys = centerline[:, 1]
    min_x = float(xs.min()) - margin
    min_y = float(ys.min()) - margin
    max_x = float(xs.max()) + margin
    max_y = float(ys.max()) + margin
    nx = int(math.ceil((max_x - min_x) / spec.resolution))
    ny = int(math.ceil((max_y - min_y) / spec.resolution))
    cx = min_x + (np.arange(nx) + 0.5) * spec.resolution
    cy = min_y + (np.arange(ny) + 0.5) * spec.resolution
    gx, gy = np.meshgrid(cx, cy, indexing="xy")
    cell_centers = np.column_stack([gx.ravel(), gy.ravel()])
    tree = cKDTree(centerline[:, :2])
    dist, _ = tree.query(cell_centers)
    occupied = dist.reshape(ny, nx) > half_width
    return (min_x, min_y), (ny, nx), occupied


def _footprint_points(
    x: float, y: float, yaw: float, length: float, width: float, resolution: float
) -> list[tuple[float, float]]:
    hl, hw = length / 2.0, width / 2.0
    corners = [(-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw)]
    local: list[tuple[float, float]] = []
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        edge_len = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(math.ceil(edge_len / resolution)))
        for j in range(n):
            t = j / n
            local.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    local.append((0.0, 0.0))
    cos, sin = math.cos(yaw), math.sin(yaw)
    return [(x + lx * cos - ly * sin, y + lx * sin + ly * cos) for lx, ly in local]


def build_track(spec: TrackSpec) -> Track:
    raw = _generate_centerline(spec.segments)
    _validate_closure(raw, spec)
    centerline, track_length, spline_x, spline_y, tree, frenet_s = _resample_and_fit(
        raw, spec.resolution
    )
    grid_origin, grid_shape, occupied = _build_grid(centerline, spec)
    return Track(
        name=spec.name,
        half_width=spec.width / 2.0,
        resolution=spec.resolution,
        track_length=track_length,
        centerline=centerline,
        spline_x=spline_x,
        spline_y=spline_y,
        grid_origin=grid_origin,
        grid_shape=grid_shape,
        occupied=occupied,
        frenet_tree=tree,
        frenet_s=frenet_s,
    )
