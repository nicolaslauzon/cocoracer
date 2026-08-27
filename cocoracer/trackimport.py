"""Import F1 circuit geometry from a GeoJSON feature into a track file."""

import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

REPO_ROOT = Path(__file__).resolve().parent.parent
GEOJSON_PATH = REPO_ROOT / "data" / "f1-circuits-geodata.geojson"
TRACKS_OUT_DIR = REPO_ROOT / "params" / "tracks"

TRACKS = {
    "cn-gv-02": "montreal",
    "bl-sf-07": "spa",
    "br-ss-11": "silverstone",
}

EARTH_RADIUS_M = 6_371_000.0

MIN_CORNER_RADIUS_M = 0.7
RESAMPLE_SPACING_M = 0.25
RING_ADJACENCY = 8
STRAIGHT_MAX_TURN_DEG = 1.0


class TrackImportError(ValueError):
    pass


def _body(points: np.ndarray) -> np.ndarray:
    if len(points) > 1 and np.allclose(points[0], points[-1]):
        return points[:-1]
    return points


def _resample_uniform(points: np.ndarray, spacing: float) -> np.ndarray:
    body = _body(points)
    closed = np.vstack([body, body[:1]])
    seg = np.hypot(closed[1:, 0] - closed[:-1, 0], closed[1:, 1] - closed[:-1, 1])
    total = float(seg.sum())
    n = max(4, math.ceil(total / spacing))
    s = np.linspace(0.0, total, n + 1)
    s_cum = np.concatenate([[0.0], np.cumsum(seg)])
    x = np.interp(s, s_cum, closed[:, 0])
    y = np.interp(s, s_cum, closed[:, 1])
    return np.column_stack([x, y])


def project_local(coords: Sequence[Sequence[float]]) -> np.ndarray:
    """Project (lon, lat) pairs into a local east/north meter frame.

    Equirectangular projection centered on the point centroid. Error is
    well under a meter for circuits under ~10 km across.
    """
    pts = np.asarray(coords, dtype=np.float64)
    lat0 = math.radians(float(pts[:, 1].mean()))
    lon0 = math.radians(float(pts[:, 0].mean()))
    x = (np.radians(pts[:, 0]) - lon0) * math.cos(lat0) * EARTH_RADIUS_M
    y = (np.radians(pts[:, 1]) - lat0) * EARTH_RADIUS_M
    return np.column_stack([x, y])


def ring_length(points: np.ndarray) -> float:
    """Length of a closed ring (last point may duplicate the first)."""
    body = _body(points)
    diffs = np.diff(np.vstack([body, body[:1]]), axis=0)
    return float(np.hypot(diffs[:, 0], diffs[:, 1]).sum())


def max_turn_angle(points: np.ndarray) -> float:
    """Largest per-vertex turn angle (radians) of a closed ring."""
    return float(_segment_turns(_body(points)).max())


def _segment_turns(body: np.ndarray) -> np.ndarray:
    nxt = np.roll(body, -1, axis=0)
    prv = np.roll(body, 1, axis=0)
    d1 = np.arctan2(body[:, 1] - prv[:, 1], body[:, 0] - prv[:, 0])
    d2 = np.arctan2(nxt[:, 1] - body[:, 1], nxt[:, 0] - body[:, 0])
    delta = d2 - d1
    turns: np.ndarray = np.abs(np.arctan2(np.sin(delta), np.cos(delta)))
    return turns


def chaikin(points: np.ndarray, iterations: int = 2) -> np.ndarray:
    """Smooth a closed ring with Chaikin corner cutting.

    Each iteration doubles the point count; the result stays closed.
    """
    pts = points
    for _ in range(iterations):
        body = _body(pts)
        nxt = np.roll(body, -1, axis=0)
        q = 0.75 * body + 0.25 * nxt
        r = 0.25 * body + 0.75 * nxt
        out = np.empty((len(body) * 2 + 1, 2))
        out[:-1:2] = q
        out[1::2] = r
        out[-1] = out[0]
        pts = out
    return pts


def resample_ring(points: np.ndarray, spacing: float) -> np.ndarray:
    """Resample a closed ring to uniform arc-length spacing.

    The result is a closed ring whose total length matches the input.
    """
    return _resample_uniform(points, spacing)


def min_corner_radius(points: np.ndarray, spacing: float = 0.5) -> float:
    """Smallest corner radius of a closed ring, in meters.

    Estimated from the turn angle at each vertex of a uniform resample:
    radius = edge_length / turn_angle. The raw point spacing does not
    affect the result. The spacing must be well below the smallest corner
    of interest, or tight corners alias away.
    """
    body = _body(_resample_uniform(points, spacing))
    d_in = body - np.roll(body, 1, axis=0)
    d_out = np.roll(body, -1, axis=0) - body
    turn = np.abs(
        np.arctan2(
            np.sin(
                np.arctan2(d_out[:, 1], d_out[:, 0])
                - np.arctan2(d_in[:, 1], d_in[:, 0])
            ),
            np.cos(
                np.arctan2(d_out[:, 1], d_out[:, 0])
                - np.arctan2(d_in[:, 1], d_in[:, 0])
            ),
        )
    )
    edge = np.hypot(d_out[:, 0], d_out[:, 1])
    radius = np.full(len(turn), np.inf)
    np.divide(edge, turn, out=radius, where=turn > 1e-9)
    return float(radius.min())


def near_self_intersection(points: np.ndarray, min_dist: float) -> bool:
    """True if two non-adjacent ring points come closer than min_dist."""
    body = _body(points)
    n = len(body)
    tree = cKDTree(body)
    dist, idx = tree.query(body, k=2)
    for i in range(n):
        j = int(idx[i, 1])
        sep = min(abs(i - j), n - abs(i - j))
        if sep > RING_ADJACENCY and float(dist[i, 1]) < min_dist:
            return True
    return False


def rotate_to_straightest_start(
    points: np.ndarray, max_turn_deg: float = STRAIGHT_MAX_TURN_DEG
) -> np.ndarray:
    """Rotate a closed ring so index 0 sits mid-way on its longest straight.

    The ring must be uniformly spaced (the per-vertex turn budget is a
    curvature measure only at a known spacing). A straight is a run of
    vertices whose turn angle is below `max_turn_deg`. Raises
    TrackImportError when no run of at least three segments exists.
    """
    body = _body(points)
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
        raise TrackImportError(
            "no straight run of 3+ segments; cannot place start line"
        )
    start = (best_start + best_len // 2) % n
    rotated = np.roll(body, -start, axis=0)
    return np.vstack([rotated, rotated[:1]])


def import_track(
    feature: dict[str, Any],
    name: str,
    scale: float = 1.0 / 12.0,
    width: float = 1.0,
    resolution: float = 0.1,
) -> dict[str, Any]:
    """Convert one GeoJSON LineString feature into a track file dict.

    Projects to local meters, applies `scale`, rotates the start to the
    longest straight, smooths and resamples, then validates closure,
    corner radius, and self-intersection.
    """
    geometry = feature["geometry"]
    if geometry["type"] != "LineString":
        raise TrackImportError(
            f"feature {name!r} is a {geometry['type']}, expected LineString"
        )
    full = project_local(geometry["coordinates"])
    gap = float(np.hypot(full[0, 0] - full[-1, 0], full[0, 1] - full[-1, 1]))
    if gap > 1.0:
        raise TrackImportError(
            f"track {name!r} is not closed: endpoint gap {gap:.1f} m"
        )
    original_length = ring_length(full)
    pts = full * scale
    pts = resample_ring(pts, 1.0)
    pts = rotate_to_straightest_start(pts)
    pts = chaikin(pts)
    pts = resample_ring(pts, RESAMPLE_SPACING_M)
    min_radius = min_corner_radius(pts)
    if min_radius < MIN_CORNER_RADIUS_M:
        raise TrackImportError(
            f"track {name!r} min corner radius {min_radius:.2f} m is below "
            f"the {MIN_CORNER_RADIUS_M} m floor"
        )
    if near_self_intersection(pts, width):
        raise TrackImportError(
            f"track {name!r} self-intersects or is narrower than its width"
        )
    props = feature.get("properties", {})
    return {
        "name": name,
        "width": width,
        "resolution": resolution,
        "source": {
            "feature": props.get("id", ""),
            "circuit": props.get("name", name),
            "variant": props.get("variant", ""),
            "orientation": props.get("orientation", ""),
        },
        "original_length_m": round(original_length, 1),
        "scale": scale,
        "centerline": [[round(float(x), 4), round(float(y), 4)] for x, y in pts],
    }


def main() -> int:
    """Import the TRACKS circuits from the vendored GeoJSON into params/tracks/."""
    data = json.loads(GEOJSON_PATH.read_text())
    TRACKS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    for feature in data["features"]:
        feature_id = feature["properties"]["id"]
        if feature_id not in TRACKS:
            continue
        track_name = TRACKS[feature_id]
        track = import_track(feature, track_name)
        out = TRACKS_OUT_DIR / f"{track_name}.json"
        out.write_text(json.dumps(track, indent=2) + "\n")
        print(
            f"{track_name:12s} {track['original_length_m']:8.1f} m full-scale"
            f"  {len(track['centerline']):5d} pts  -> {out.relative_to(REPO_ROOT)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
