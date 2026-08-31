"""Full-circle fleet laser scan: walls and racing vehicles.

``fleet_scan`` hands every vehicle in a fleet one full-circle scan:
walls, marched over the track's occupancy grid, plus the collision
circles of the racing vehicles, tested by closed-form ray-circle
intersection. First hit wins per beam; a beam that hits nothing
reports ``np.inf``. Only racing vehicles block a beam — ghosts and
paused vehicles are invisible — and no vehicle sees itself.
"""

import numpy as np

from cocoracer.track import Track
from cocoracer.vehicle import Vehicle


def fleet_scan(
    track: Track,
    fleet: list[Vehicle],
    beam_angles: np.ndarray,
    collision_distance: float,
) -> np.ndarray:
    """Full-circle laser scan for every vehicle in the fleet.

    Args:
        track: The track whose occupancy grid is scanned.
        fleet: The vehicles to scan, in order; result row i is the scan
            of the vehicle at fleet index i.
        beam_angles: (B,) beam angles in radians, relative to vehicle
            heading; beam 0 points straight ahead.
        collision_distance: radius of a vehicle's collision circle in
            meters.

    Returns:
        (N, B) array; entry (i, j) is the distance from fleet vehicle i
        to the first obstacle — a wall, or a racing vehicle's collision
        circle — along beam j, or ``np.inf`` if the beam hits nothing.
    """
    n = len(fleet)
    poses = np.array([[v.x, v.y, v.yaw] for v in fleet])
    scans = track.beam_distances(poses, beam_angles)
    exclude = np.full(n, -1, dtype=np.intp)
    targets: list[Vehicle] = []
    for i, v in enumerate(fleet):
        if v.state.is_racing:
            exclude[i] = len(targets)
            targets.append(v)
    if targets:
        target_poses = np.array([[v.x, v.y] for v in targets])
        scans = np.minimum(
            scans,
            _vehicle_hits(
                poses, beam_angles, target_poses, exclude, collision_distance
            ),
        )
    return scans


def _vehicle_hits(
    poses: np.ndarray,
    beam_angles: np.ndarray,
    target_poses: np.ndarray,
    exclude: np.ndarray,
    radius: float,
) -> np.ndarray:
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
    return np.asarray(t.min(axis=2).reshape(n, b))
