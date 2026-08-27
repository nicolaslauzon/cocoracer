import numpy as np
import pytest
from scipy.spatial import cKDTree

from cocoracer.config import Segment, TrackSpec
from cocoracer.track import Track, TrackError, build_track


def wrap(a: float) -> float:
    return (a + np.pi) % (2 * np.pi) - np.pi


def test_stadium_closes(stadium: Track) -> None:
    assert stadium.track_length > 0
    first, last = stadium.centerline[0], stadium.centerline[-1]
    assert np.allclose([first[0], first[1]], [last[0], last[1]], atol=1e-6)
    assert abs(wrap(first[2] - last[2])) < 1e-6


def test_stadium_centerline_uniform_spacing(stadium: Track) -> None:
    xy = stadium.centerline_xy
    steps = np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))
    assert np.allclose(steps, steps[0], rtol=1e-2, atol=1e-3)


def test_frenet_roundtrip_centerline(stadium: Track) -> None:
    for s in (0.0, 1.0, 3.7, 6.25, 10.0, 15.0, stadium.track_length - 0.4):
        x, y, psi = stadium.to_cartesian(s, 0.0)
        s2, d2, dyaw = stadium.to_frenet(x, y, psi)
        assert s2 == pytest.approx(s, abs=5e-3)
        assert d2 == pytest.approx(0.0, abs=5e-3)
        assert dyaw == pytest.approx(0.0, abs=5e-3)


def test_frenet_roundtrip_lateral(stadium: Track) -> None:
    s, d = 2.5, 0.2
    x, y, psi = stadium.to_cartesian(s, d)
    s2, d2, _ = stadium.to_frenet(x, y, psi)
    assert s2 == pytest.approx(s, abs=5e-3)
    assert d2 == pytest.approx(d, abs=5e-3)


def test_grid_marks_exactly_beyond_half_width(stadium: Track) -> None:
    ox, oy = stadium.grid_origin
    ny, nx = stadium.grid_shape
    cx = ox + (np.arange(nx) + 0.5) * stadium.resolution
    cy = oy + (np.arange(ny) + 0.5) * stadium.resolution
    gx, gy = np.meshgrid(cx, cy, indexing="xy")
    tree = cKDTree(stadium.centerline[:, :2])
    dist, _ = tree.query(np.column_stack([gx.ravel(), gy.ravel()]))
    expected = dist.reshape(ny, nx) > stadium.half_width
    assert np.array_equal(stadium.occupied, expected)


def test_closure_rejects_bad_turn_sum() -> None:
    spec = TrackSpec(
        name="bad_angle",
        width=1.0,
        resolution=0.05,
        segments=[
            Segment("straight", length=6.0),
            Segment("turn", radius=2.0, angle=90.0),
            Segment("straight", length=6.0),
            Segment("turn", radius=2.0, angle=180.0),
        ],
    )
    with pytest.raises(TrackError):
        build_track(spec)


def test_closure_rejects_open_endpoint() -> None:
    spec = TrackSpec(
        name="open",
        width=1.0,
        resolution=0.05,
        segments=[
            Segment("straight", length=6.0),
            Segment("turn", radius=2.0, angle=180.0),
            Segment("straight", length=3.0),
            Segment("turn", radius=2.0, angle=180.0),
        ],
    )
    with pytest.raises(TrackError):
        build_track(spec)
