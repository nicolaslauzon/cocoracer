import math

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

from cocoracer.config import TrackSpec


class TrackError(ValueError):
    pass


def wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


STRAIGHT_MAX_TURN_DEG = 1.0


def _ring_body(points: np.ndarray) -> np.ndarray:
    if len(points) > 1 and np.allclose(points[0], points[-1]):
        return points[:-1]
    return points


def _segment_turns(body: np.ndarray) -> np.ndarray:
    nxt = np.roll(body, -1, axis=0)
    prv = np.roll(body, 1, axis=0)
    d1 = np.arctan2(body[:, 1] - prv[:, 1], body[:, 0] - prv[:, 0])
    d2 = np.arctan2(nxt[:, 1] - body[:, 1], nxt[:, 0] - body[:, 0])
    delta = d2 - d1
    turns: np.ndarray = np.abs(np.arctan2(np.sin(delta), np.cos(delta)))
    return turns


def rotate_to_straightest_start(
    points: np.ndarray, max_turn_deg: float = STRAIGHT_MAX_TURN_DEG
) -> np.ndarray:
    """Rotate a closed ring so index 0 sits mid-way on its longest straight.

    The ring must be uniformly spaced (the per-vertex turn budget is a
    curvature measure only at a known spacing). A straight is a run of
    vertices whose turn angle is below `max_turn_deg`. Raises
    TrackError when no run of at least three segments exists.
    """
    body = _ring_body(points)
    n = len(body)
    ok = _segment_turns(body) < math.radians(max_turn_deg)
    best_start, best_len = 0, 0
    run_start, run_len = 0, 0
    for i in range(2 * n):
        if ok[i % n]:
            if run_len == 0:
                run_start = i
            run_len += 1
            if 0 < run_len <= n and run_len > best_len:
                best_start, best_len = run_start, run_len
        else:
            run_len = 0
    if best_len < 3:
        raise TrackError("no straight run of 3+ segments; cannot place start line")
    start = (best_start + best_len // 2) % n
    rotated = np.roll(body, -start, axis=0)
    return np.vstack([rotated, rotated[:1]])


class Track:
    def __init__(
        self,
        name: str,
        width: float,
        resolution: float,
        track_length: float,
        centerline: np.ndarray,
        left_wall: np.ndarray,
        right_wall: np.ndarray,
        spline_x: CubicSpline,
        spline_y: CubicSpline,
        grid_origin: tuple[float, float],
        grid_shape: tuple[int, int],
        occupied: np.ndarray,
        frenet_tree: cKDTree,
        frenet_s: np.ndarray,
    ) -> None:
        self.name = name
        self.width = width
        self.resolution = resolution
        self.track_length = track_length
        self.centerline = centerline
        self.left_wall = left_wall
        self.right_wall = right_wall
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

    def beam_distances(self, poses: np.ndarray, beam_angles: np.ndarray) -> np.ndarray:
        """Distance from each pose to the first wall along each beam.

        Marches each beam over the occupancy grid at grid-resolution
        steps. There is no max range: a beam that hits no occupied cell
        reports ``np.inf``.
        """
        res = self.resolution
        ox, oy = self.grid_origin
        ny, nx = self.grid_shape
        occupied = self.occupied

        n = poses.shape[0]
        b = beam_angles.shape[0]
        x = poses[:, 0]
        y = poses[:, 1]
        theta = poses[:, 2][:, None] + beam_angles[None, :]
        px = np.repeat(x, b)
        py = np.repeat(y, b)
        dx = np.cos(theta).ravel()
        dy = np.sin(theta).ravel()

        x_max = ox + nx * res
        y_max = oy + ny * res
        start_d2 = _dist2_to_grid(px, py, ox, oy, x_max, y_max)
        diag = int(np.ceil(np.hypot(nx, ny)))
        max_steps = diag + int(np.ceil(np.sqrt(start_d2.max()) / res)) + 1

        dist = np.full(px.shape, np.inf)
        alive = np.ones(px.shape, dtype=bool)
        prev_d2 = start_d2
        for k in range(1, max_steps + 1):
            if not alive.any():
                break
            d = k * res
            sx = px + d * dx
            sy = py + d * dy
            ix = np.floor((sx - ox) / res).astype(np.intp)
            iy = np.floor((sy - oy) / res).astype(np.intp)
            in_bounds = alive & (ix >= 0) & (iy >= 0) & (ix < nx) & (iy < ny)
            hit = in_bounds & occupied[np.clip(iy, 0, ny - 1), np.clip(ix, 0, nx - 1)]
            if hit.any():
                dist[hit] = d
                alive &= ~hit
            # The grid is convex, so a ray's distance to it decreases then
            # increases: once an out-of-grid ray is moving away, it can never
            # re-enter, and the march ends with a no-hit.
            d2 = _dist2_to_grid(sx, sy, ox, oy, x_max, y_max)
            escaped = alive & ~in_bounds & (d2 > prev_d2 + 1e-12)
            if escaped.any():
                alive &= ~escaped
            prev_d2 = np.where(alive, d2, prev_d2)
        return dist.reshape(n, b)


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
    segments = spec.segments
    if segments is None:
        raise TrackError(f"track {spec.name!r} has no layout")
    turn_sum = sum(seg.angle for seg in segments if seg.type == "turn")
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
    # The cells beyond the band between the two synthesized walls are
    # exactly the cells farther than half the width from the centerline.
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


def _offset_walls(
    centerline: np.ndarray,
    s: np.ndarray,
    spline_x: CubicSpline,
    spline_y: CubicSpline,
    offset_left: float | np.ndarray,
    offset_right: float | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    dx = spline_x(s, 1)
    dy = spline_y(s, 1)
    norm = np.hypot(dx, dy)
    nx = -dy / norm
    ny = dx / norm
    left = np.column_stack(
        [centerline[:, 0] + offset_left * nx, centerline[:, 1] + offset_left * ny]
    )
    right = np.column_stack(
        [centerline[:, 0] - offset_right * nx, centerline[:, 1] - offset_right * ny]
    )
    return left, right


def _median_width(
    centerline: np.ndarray, left_wall: np.ndarray, right_wall: np.ndarray
) -> float:
    cl = centerline[:-1, :2]
    left_d, _ = cKDTree(left_wall).query(cl)
    right_d, _ = cKDTree(right_wall).query(cl)
    return float(np.median(left_d + right_d))


def _validate_walls(name: str, left_wall: np.ndarray, right_wall: np.ndarray) -> None:
    for label, wall in (("left", left_wall), ("right", right_wall)):
        if wall.ndim != 2 or wall.shape[1] != 2 or len(wall) < 3:
            raise TrackError(
                f"track {name!r} {label} wall must be an (N, 2) array "
                "of at least 3 points"
            )
        gap = math.hypot(wall[0, 0] - wall[-1, 0], wall[0, 1] - wall[-1, 1])
        if gap > 0.1:
            raise TrackError(
                f"track {name!r} {label} wall does not close: endpoint gap {gap:.4f} m"
            )


def _dist2_to_grid(
    x: np.ndarray, y: np.ndarray, ox: float, oy: float, x_max: float, y_max: float
) -> np.ndarray:
    dx = np.where(x < ox, ox - x, np.where(x > x_max, x - x_max, 0.0))
    dy = np.where(y < oy, oy - y, np.where(y > y_max, y - y_max, 0.0))
    d2: np.ndarray = dx * dx + dy * dy
    return d2


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


def _centerline_to_raw(points: list[tuple[float, float]], name: str) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 4:
        raise TrackError(
            f"track {name!r} centerline must have at least 4 [x, y] points"
        )
    gap = math.hypot(pts[0, 0] - pts[-1, 0], pts[0, 1] - pts[-1, 1])
    if gap > 0.1:
        raise TrackError(
            f"track {name!r} centerline does not close: endpoint gap {gap:.4f} m"
        )
    body = pts[:-1] if gap < 1e-9 else pts
    nxt = np.roll(body, -1, axis=0)
    prv = np.roll(body, 1, axis=0)
    heading = np.arctan2(nxt[:, 1] - prv[:, 1], nxt[:, 0] - prv[:, 0])
    yaw = np.unwrap(heading)
    raw = np.column_stack([body, yaw])
    return np.vstack([raw, [raw[0, 0], raw[0, 1], yaw[0]]])


def build_track(
    spec: TrackSpec,
    walls: tuple[np.ndarray, np.ndarray] | None = None,
    grid: tuple[tuple[float, float], tuple[int, int], np.ndarray] | None = None,
) -> Track:
    """Build a Track from a layout spec.

    A spec with a map delegates to the map build, which reads the
    centerline CSV and metadata YAML derived from the map image path.
    Without `walls`, both walls are synthesized at +/-spec.width/2 around
    the centerline (the constant-width case) and the occupancy grid is
    built from that band. A map-based build passes explicit left/right wall
    curves together with an explicit grid; the two are required as a pair.
    The reported width is always the median wall-to-wall distance along the
    centerline, so a constant-width track reports its configured width.
    """
    if spec.map is not None:
        from cocoracer.maptrack import build_map_track

        m = spec.map
        return build_map_track(
            spec.name,
            m.image.with_suffix(".csv"),
            m.image.with_suffix(".yaml"),
            m.image,
            m.direction,
            m.start,
            scale=m.scale,
            threshold=m.threshold,
        )
    if spec.centerline is not None:
        raw = _centerline_to_raw(spec.centerline, spec.name)
    else:
        if spec.segments is None:
            raise TrackError(f"track {spec.name!r} has no layout")
        raw = _generate_centerline(spec.segments)
        _validate_closure(raw, spec)
    centerline, track_length, spline_x, spline_y, tree, frenet_s = _resample_and_fit(
        raw, spec.resolution
    )
    if walls is None:
        s_vals = np.concatenate([frenet_s, [0.0]])
        left_wall, right_wall = _offset_walls(
            centerline, s_vals, spline_x, spline_y, spec.width / 2.0, spec.width / 2.0
        )
        if grid is None:
            grid = _build_grid(centerline, spec)
    else:
        left_wall, right_wall = walls
        _validate_walls(spec.name, left_wall, right_wall)
        if grid is None:
            raise TrackError(
                f"track {spec.name!r} with explicit walls needs an explicit grid"
            )
    grid_origin, grid_shape, occupied = grid
    return Track(
        name=spec.name,
        width=_median_width(centerline, left_wall, right_wall),
        resolution=spec.resolution,
        track_length=track_length,
        centerline=centerline,
        left_wall=left_wall,
        right_wall=right_wall,
        spline_x=spline_x,
        spline_y=spline_y,
        grid_origin=grid_origin,
        grid_shape=grid_shape,
        occupied=occupied,
        frenet_tree=tree,
        frenet_s=frenet_s,
    )
