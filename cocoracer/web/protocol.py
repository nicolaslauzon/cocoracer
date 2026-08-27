"""Pure state-to-JSON serializers for the live view's WebSocket.

Two message kinds flow over the connection. One **static** message per
connection carries everything about the track that never changes:
centerline, occupancy grid as origin/resolution/occupied cells, track
width, and the start line. Then **dynamic** messages carry the moving
parts: sim time, phase, countdown, and per-vehicle state including each
vehicle's last laser scan. ``null`` stands for a no-hit beam
(``np.inf`` in-process) and for laps, times, and scans that do not
exist yet.
"""

import json
from collections.abc import Sequence

import numpy as np

from cocoracer.engine import RaceSnapshot
from cocoracer.track import Track


def _scan_list(scan: np.ndarray | None) -> list[float | None] | None:
    if scan is None:
        return None
    return [None if np.isinf(d) else float(d) for d in scan]


def build_static_message(track: Track) -> str:
    """Serialize the track's static data into the connect message."""
    ox, oy = track.grid_origin
    ny, nx = track.grid_shape
    cells = [[int(ix), int(iy)] for iy, ix in np.argwhere(track.occupied)]
    x, y, yaw = track.start_pose
    message = {
        "type": "static",
        "track": track.name,
        "centerline": [[float(px), float(py)] for px, py in track.centerline[:, :2]],
        "grid": {
            "origin": [float(ox), float(oy)],
            "resolution": float(track.resolution),
            "width": int(nx),
            "height": int(ny),
            "occupied": cells,
        },
        "track_width": float(track.half_width * 2.0),
        "start_line": {"x": float(x), "y": float(y), "yaw": float(yaw)},
    }
    return json.dumps(message)


def build_dynamic_message(
    snapshot: RaceSnapshot,
    phase: str,
    countdown: float,
    scans: Sequence[np.ndarray | None],
) -> str:
    """Serialize one dynamic snapshot into a WebSocket message.

    Args:
        snapshot: The race's read-only snapshot at one moment.
        phase: "countdown", "racing", or "finished".
        countdown: Countdown time remaining, in seconds (0.0 once
            released or when the mode has no countdown).
        scans: Each vehicle's last laser scan, in vehicle order; None
            for a vehicle that has not been stepped yet.
    """
    vehicles = []
    for snap, scan in zip(snapshot.vehicles, scans, strict=True):
        vehicles.append(
            {
                "id": int(snap.id),
                "name": snap.name,
                "x": float(snap.x),
                "y": float(snap.y),
                "yaw": float(snap.yaw),
                "speed": float(snap.speed),
                "steering": float(snap.steering),
                "laps": int(snap.laps_completed),
                "status": snap.status.value,
                "best_lap": snap.best_lap,
                "last_lap": snap.last_lap,
                "crashes": int(snap.crashes),
                "finish_time": snap.finish_time,
                "scan": _scan_list(scan),
            }
        )
    message = {
        "type": "dynamic",
        "time": float(snapshot.time),
        "phase": phase,
        "countdown": float(countdown),
        "vehicles": vehicles,
    }
    return json.dumps(message)
