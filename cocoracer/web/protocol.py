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
import struct
import zlib
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from cocoracer.config import Config
from cocoracer.engine import RaceSnapshot
from cocoracer.pgm import parse_pgm
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


def map_display_image(config: Config, track_name: str) -> Path | None:
    """The display PGM of a map track, or None for non-map tracks.

    Prefers the ``-gimp`` display variant (the same picture with the wall
    outlines drawn in); falls back to the clean image when no display
    variant ships.
    """
    spec = config.tracks.get(track_name)
    map_spec = spec.map if spec is not None else None
    if map_spec is None:
        return None
    display = map_spec.image.with_name(f"{map_spec.image.stem}-gimp.pgm")
    return display if display.is_file() else map_spec.image


def pgm_png_bytes(image: np.ndarray) -> bytes:
    """Encode a uint8 grayscale image as a PNG (stdlib-only writer)."""
    height, width = image.shape
    raw = b"".join(b"\x00" + row.tobytes() for row in image)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)),
            chunk(b"IDAT", zlib.compress(raw)),
            chunk(b"IEND", b""),
        ]
    )


def map_image_block(config: Config, track_name: str) -> dict | None:
    """Placement data for the map's display image, in the track world.

    The world frame of a map track is image pixels times the map's scale
    (meters per pixel), origin at the image's bottom-left corner, y up.
    """
    spec = config.tracks.get(track_name)
    map_spec = spec.map if spec is not None else None
    if map_spec is None:
        return None
    path = map_display_image(config, track_name)
    if path is None:
        return None
    image = parse_pgm(path)
    height, width = image.shape
    return {
        "url": "/map-image",
        "scale": float(map_spec.scale),
        "width": int(width),
        "height": int(height),
    }


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
        "map_image": map_image_block(config, track.name),
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
                "last_crash": None
                if snap.last_crash is None
                else {"x": float(snap.last_crash[0]), "y": float(snap.last_crash[1])},
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
