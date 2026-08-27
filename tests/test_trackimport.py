import json
import math
from pathlib import Path

import numpy as np
import pytest

from cocoracer.trackimport import (
    GEOJSON_PATH,
    TRACKS,
    TrackImportError,
    chaikin,
    import_track,
    min_corner_radius,
    near_self_intersection,
    project_local,
    resample_ring,
    ring_length,
    rotate_to_straightest_start,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _circle_ring(r: float, n: int) -> np.ndarray:
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    body = np.column_stack([r * np.cos(t), r * np.sin(t)])
    return np.vstack([body, body[:1]])


def _rect_ring(w: float, h: float, step: float) -> np.ndarray:
    nx, ny = int(round(w / step)), int(round(h / step))
    pts: list[list[float]] = []
    for i in range(nx + 1):
        pts.append([i * step, 0.0])
    for i in range(1, ny + 1):
        pts.append([w, i * step])
    for i in range(1, nx + 1):
        pts.append([w - i * step, h])
    for i in range(1, ny):
        pts.append([0.0, h - i * step])
    pts.append([0.0, 0.0])
    return np.asarray(pts, dtype=np.float64)


def _trapezoid_ring() -> np.ndarray:
    pts: list[list[float]] = [[0.0, 0.0]]
    for i in range(1, 25):
        pts.append([i * 0.5, 0.0])
    for i in range(1, 9):
        pts.append([12.0 - 0.25 * i, 0.5 * i])
    for i in range(1, 17):
        pts.append([10.0 - 0.5 * i, 4.0])
    for i in range(1, 8):
        pts.append([2.0 - 0.25 * i, 4.0 - 0.5 * i])
    pts.append([0.0, 0.0])
    return np.asarray(pts, dtype=np.float64)


def _lemniscate_ring(n: int) -> np.ndarray:
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    body = np.column_stack([np.cos(t), np.sin(t) * np.cos(t)])
    return np.vstack([body, body[:1]])


def test_project_local_scales_degrees_to_meters() -> None:
    pts = project_local([(10.0, 50.0), (10.001, 50.001)])
    lat0 = math.radians(50.0005)
    dx = pts[1, 0] - pts[0, 0]
    dy = pts[1, 1] - pts[0, 1]
    assert dx == pytest.approx(
        math.radians(0.001) * math.cos(lat0) * 6_371_000.0, rel=1e-9
    )
    assert dy == pytest.approx(math.radians(0.001) * 6_371_000.0, rel=1e-9)


def test_ring_length_closed_square() -> None:
    assert ring_length(_rect_ring(10.0, 4.0, 1.0)) == pytest.approx(28.0, abs=1e-9)


def test_chaikin_closes_and_smooths() -> None:
    ring = _rect_ring(10.0, 4.0, 1.0)
    single = chaikin(ring, iterations=1)
    assert len(single) - 1 == 2 * (len(ring) - 1)
    out = chaikin(ring)
    assert np.allclose(out[0], out[-1])
    for axis in range(2):
        assert float(out[:, axis].max()) <= float(ring[:, axis].max()) + 1e-9
        assert float(out[:, axis].min()) >= float(ring[:, axis].min()) - 1e-9
    turns = _turns(ring)
    out_turns = _turns(out)
    assert out_turns.max() < turns.max()


def _turns(ring: np.ndarray) -> np.ndarray:
    body = ring[:-1]
    d_in = body - np.roll(body, 1, axis=0)
    d_out = np.roll(body, -1, axis=0) - body
    a1 = np.arctan2(d_in[:, 1], d_in[:, 0])
    a2 = np.arctan2(d_out[:, 1], d_out[:, 0])
    delta = a2 - a1
    turns: np.ndarray = np.abs(np.arctan2(np.sin(delta), np.cos(delta)))
    return turns


def test_resample_uniform_spacing() -> None:
    ring = _circle_ring(10.0, 200)
    out = resample_ring(ring, 0.5)
    assert np.allclose(out[0], out[-1])
    body = out[:-1]
    steps = np.hypot(
        np.diff(np.vstack([body, body[:1]])[:, 0]),
        np.diff(np.vstack([body, body[:1]])[:, 1]),
    )
    assert np.allclose(steps, steps.mean(), rtol=1e-3)
    assert ring_length(out) == pytest.approx(ring_length(ring), rel=1e-3)


def test_min_corner_radius_dense_circle() -> None:
    assert min_corner_radius(_circle_ring(10.0, 2000)) == pytest.approx(10.0, abs=0.01)


def test_min_corner_radius_sharp_corner() -> None:
    assert min_corner_radius(_rect_ring(10.0, 4.0, 0.5)) == pytest.approx(
        0.5 / (math.pi / 2.0), abs=1e-9
    )


def test_near_self_intersection_simple_ring() -> None:
    assert not near_self_intersection(_circle_ring(1.5, 400), 0.1)


def test_near_self_intersection_crossing_ring() -> None:
    assert near_self_intersection(_lemniscate_ring(800), 0.1)


def test_rotate_start_lands_mid_longest_straight() -> None:
    out = rotate_to_straightest_start(_trapezoid_ring())
    assert np.allclose(out[0], out[-1])
    assert out[0] == pytest.approx([6.0, 0.0], abs=0.01)
    assert abs(out[1, 1] - out[0, 1]) < 1e-9


def test_rotate_start_requires_straight() -> None:
    with pytest.raises(TrackImportError):
        rotate_to_straightest_start(_circle_ring(10.0, 60))


def test_import_track_rejects_non_linestring() -> None:
    feature = {
        "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
        "properties": {"id": "x"},
    }
    with pytest.raises(TrackImportError, match="LineString"):
        import_track(feature, "x")


def test_import_track_rejects_open_ring() -> None:
    body = _circle_ring(10.0, 100)[:-1]
    feature = {
        "geometry": {"type": "LineString", "coordinates": [list(p) for p in body]},
        "properties": {},
    }
    with pytest.raises(TrackImportError, match="not closed"):
        import_track(feature, "open")


@pytest.mark.parametrize("feature_id", sorted(TRACKS))
def test_import_track_matches_committed_file(feature_id: str) -> None:
    name = TRACKS[feature_id]
    data = json.loads(GEOJSON_PATH.read_text())
    feature = next(f for f in data["features"] if f["properties"]["id"] == feature_id)
    track = import_track(feature, name)
    committed = json.loads(
        (REPO_ROOT / "params" / "tracks" / f"{name}.json").read_text()
    )
    assert track == committed


@pytest.mark.parametrize(
    ("feature_id", "official_length_m"),
    [("cn-gv-02", 4361.0), ("bl-sf-07", 7004.0), ("br-ss-11", 5891.0)],
)
def test_import_track_length_matches_official(
    feature_id: str, official_length_m: float
) -> None:
    data = json.loads(GEOJSON_PATH.read_text())
    feature = next(f for f in data["features"] if f["properties"]["id"] == feature_id)
    track = import_track(feature, TRACKS[feature_id])
    assert track["original_length_m"] == pytest.approx(official_length_m, rel=0.01)
