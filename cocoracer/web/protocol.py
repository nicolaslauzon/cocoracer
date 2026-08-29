"""Pure state-to-JSON serializers for the live view's WebSocket.

Two message kinds flow over the connection. One **static** message per
connection carries everything about the track that never changes:
centerline, the two wall curves (downsampled to ~1 m for the payload),
track length, vehicle dimensions, and the start line. Then **dynamic**
messages carry the moving parts: sim time, phase, countdown, and
per-vehicle state including each vehicle's last laser scan. ``null``
stands for a no-hit beam (``np.inf`` in-process) and for laps, times,
and scans that do not exist yet.
"""

import json
import math
from collections.abc import Sequence

import numpy as np

from cocoracer.config import Config
from cocoracer.engine import RaceSnapshot
from cocoracer.track import Track

_WALL_SEND_SPACING = 1.0


def _scan_list(scan: np.ndarray | None) -> list[float | None] | None:
    if scan is None:
        return None
    return [None if np.isinf(d) else float(d) for d in scan]


def _downsample(points: np.ndarray, spacing: float) -> np.ndarray:
    seg = np.hypot(np.diff(points[:, 0]), np.diff(points[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(s[-1])
    n = max(3, int(math.ceil(total / spacing)))
    s_new = np.linspace(0.0, total, n, endpoint=True)
    out = np.column_stack(
        [np.interp(s_new, s, points[:, 0]), np.interp(s_new, s, points[:, 1])]
    )
    out[-1] = out[0]
    return out


def _point(p: np.ndarray) -> list[float]:
    return [float(p[0]), float(p[1])]


def _points(points: np.ndarray) -> list[list[float]]:
    return [[float(px), float(py)] for px, py in points]


def build_static_message(track: Track, config: Config) -> str:
    """Serialize the track's static data into the connect message."""
    message = {
        "type": "static",
        "track": track.name,
        "centerline": _points(track.centerline[:, :2]),
        "left_wall": _points(_downsample(track.left_wall, _WALL_SEND_SPACING)),
        "right_wall": _points(_downsample(track.right_wall, _WALL_SEND_SPACING)),
        "track_length": float(track.track_length),
        "vehicle": {
            "length": float(config.vehicle.length),
            "width": float(config.vehicle.width),
        },
        "start_line": {
            "left": _point(track.left_wall[0]),
            "right": _point(track.right_wall[0]),
        },
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
        phase: "waiting", "countdown", "racing", or "finished".
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
