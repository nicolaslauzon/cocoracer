"""Full-circle laser scan: walls and other vehicles.

``scan_walls`` marches each beam over the track's occupancy grid at
grid-resolution steps and stops at the first occupied cell.
``scan_vehicles`` tests the same beams against other vehicles as
circles via closed-form ray-circle intersection. There is no max range:
a beam that hits nothing reports ``np.inf``. Both scans are vectorized
over beams and vehicles — one call covers an entire fleet's worth of
rays.
"""

import numpy as np

from cocoracer.track import Track


def scan_walls(track: Track, poses: np.ndarray, beam_angles: np.ndarray) -> np.ndarray:
    """Distance from each vehicle to the first wall along each beam.

    Args:
        track: The track whose occupancy grid is scanned.
        poses: (N, 3) array of vehicle x, y, yaw (yaw in radians).
        beam_angles: (B,) beam angles in radians, relative to vehicle
            heading; beam 0 points straight ahead.

    Returns:
        (N, B) array; entry (i, j) is the distance from vehicle i to the
        first occupied cell along beam j, or ``np.inf`` if the beam hits
        no occupied cell.
    """
    res = track.resolution
    ox, oy = track.grid_origin
    ny, nx = track.grid_shape
    occupied = track.occupied

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


def scan_vehicles(
    poses: np.ndarray,
    beam_angles: np.ndarray,
    target_poses: np.ndarray,
    exclude: np.ndarray,
    radius: float,
) -> np.ndarray:
    """Distance from each vehicle to the nearest target vehicle per beam.

    Args:
        poses: (N, 3) array of vehicle x, y, yaw (yaw in radians).
        beam_angles: (B,) beam angles in radians, relative to vehicle
            heading; beam 0 points straight ahead.
        target_poses: (M, 2) array of target vehicle x, y.
        exclude: (N,) array; entry i is the index into ``target_poses``
            of the scanner's own body (skipped for that scanner), or -1
            if the scanner is not among the targets.
        radius: target vehicle collision radius in meters.

    Returns:
        (N, B) array; entry (i, j) is the distance from vehicle i to the
        nearest target along beam j, or ``np.inf`` if the beam hits no
        target.
    """
    n = poses.shape[0]
    b = beam_angles.shape[0]
    m = target_poses.shape[0]
    x = poses[:, 0]
    y = poses[:, 1]
    theta = poses[:, 2][:, None] + beam_angles[None, :]
    fx = target_poses[None, None, :, 0] - x[:, None, None]
    fy = target_poses[None, None, :, 1] - y[:, None, None]
    # Ray o + t d vs circle c, r: f = c - o, t = d.f +/- sqrt((d.f)^2 -
    # (|f|^2 - r^2)). The near root is used when it is positive, else the
    # far root (origin inside the circle); roots are clipped to t > 0 so
    # a beam touching a target exactly at the origin is not a hit.
    df = np.cos(theta)[:, :, None] * fx + np.sin(theta)[:, :, None] * fy
    disc = df * df - (fx * fx + fy * fy - radius * radius)
    sqrt_disc = np.sqrt(np.maximum(disc, 0.0))
    t = np.where(df - sqrt_disc > 0.0, df - sqrt_disc, df + sqrt_disc)
    t = np.where((disc >= 0.0) & (t > 0.0), t, np.inf)
    own = np.arange(m)[None, None, :] == exclude[:, None, None]
    t = np.where(own, np.inf, t)
    return t.min(axis=2).reshape(n, b)


def _dist2_to_grid(
    x: np.ndarray, y: np.ndarray, ox: float, oy: float, x_max: float, y_max: float
) -> np.ndarray:
    dx = np.where(x < ox, ox - x, np.where(x > x_max, x - x_max, 0.0))
    dy = np.where(y < oy, oy - y, np.where(y > y_max, y - y_max, 0.0))
    d2: np.ndarray = dx * dx + dy * dy
    return d2
