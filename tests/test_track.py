from collections.abc import Callable

import numpy as np
import pytest
from scipy.spatial import cKDTree

from cocoracer.config import Config, Segment, TrackSpec
from cocoracer.track import (
    Track,
    TrackError,
    build_track,
)


def wrap(a: float) -> float:
    return (a + np.pi) % (2 * np.pi) - np.pi


def _angles(count: int) -> np.ndarray:
    return np.arange(count) * (2.0 * np.pi / count)


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


def test_stadium_grid_matches_wall_band(stadium: Track) -> None:
    ox, oy = stadium.grid_origin
    ny, nx = stadium.grid_shape
    cx = ox + (np.arange(nx) + 0.5) * stadium.resolution
    cy = oy + (np.arange(ny) + 0.5) * stadium.resolution
    gx, gy = np.meshgrid(cx, cy, indexing="xy")
    tree = cKDTree(stadium.centerline[:, :2])
    dist, _ = tree.query(np.column_stack([gx.ravel(), gy.ravel()]))
    expected = dist.reshape(ny, nx) > stadium.width / 2.0
    assert np.array_equal(stadium.occupied, expected)


def test_stadium_grid_cells_are_0_3_m(stadium: Track) -> None:
    assert stadium.resolution == pytest.approx(0.3)


def test_stadium_walls_closed_and_offset_from_centerline(stadium: Track) -> None:
    cl = stadium.centerline[:, :2]
    tangent = np.column_stack(
        [np.cos(stadium.centerline[:, 2]), np.sin(stadium.centerline[:, 2])]
    )
    for wall, side in ((stadium.left_wall, 1.0), (stadium.right_wall, -1.0)):
        assert wall.shape == (len(cl), 2)
        assert np.allclose(wall[0], wall[-1])
        off = wall - cl
        assert np.allclose(np.linalg.norm(off, axis=1), stadium.width / 2.0, atol=1e-6)
        cross = tangent[:, 0] * off[:, 1] - tangent[:, 1] * off[:, 0]
        assert np.all(np.sign(cross) == side)


def test_stadium_reported_width_is_configured(stadium: Track, config: Config) -> None:
    assert stadium.width == pytest.approx(config.tracks["stadium"].width)


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


def test_beam_distances_read_known_wall(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = synthetic_track_factory(occupied)
    scan = track.beam_distances(np.array([[0.0, 1.0, 0.0]]), _angles(72))
    # Grid-sampled hits land within ~1.5 resolutions of the true wall face:
    # occupancy is judged at cell centers, so the first occupied sample can
    # sit one full step past the face.
    assert scan[0, 0] == pytest.approx(1.1, abs=0.15)


def test_beam_distances_first_obstacle_wins(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 5:7] = True
    occupied[:, 12:14] = True
    track = synthetic_track_factory(occupied)
    scan = track.beam_distances(np.array([[0.0, 1.0, 0.0]]), _angles(72))
    assert scan[0, 0] == pytest.approx(0.5, abs=0.15)


def test_beam_distances_no_hit_reads_inf(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    track = synthetic_track_factory(occupied)
    scan = track.beam_distances(np.array([[1.0, 1.0, 0.0]]), _angles(72))
    assert np.all(np.isinf(scan))


def test_beam_distances_hit_only_the_wall_that_is_there(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[15:, :] = True
    track = synthetic_track_factory(occupied)
    scan = track.beam_distances(np.array([[1.0, 0.05, 0.0]]), _angles(72))
    assert scan[0, 18] == pytest.approx(1.5, abs=0.15)
    assert np.isinf(scan[0, 0])
    assert np.isinf(scan[0, 54])


def test_beam_distances_multiple_vehicles_in_one_call(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = synthetic_track_factory(occupied)
    poses = np.array([[0.0, 1.0, 0.0], [0.0, 1.0, np.pi]])
    scan = track.beam_distances(poses, _angles(72))
    assert scan.shape == (2, 72)
    assert scan[0, 0] == pytest.approx(1.1, abs=0.15)
    assert np.isinf(scan[1, 0])
    assert scan[1, 36] == pytest.approx(1.1, abs=0.15)


def _rect_points() -> list[tuple[float, float]]:
    pts = [(float(x), 0.0) for x in np.arange(0.0, 10.1, 0.5)]
    pts += [(10.0, float(y)) for y in np.arange(0.5, 4.5, 0.5)]
    pts += [(float(x), 4.0) for x in np.arange(9.5, -0.01, -0.5)]
    pts += [(0.0, float(y)) for y in np.arange(3.5, -0.01, -0.5)]
    pts.append((0.0, 0.0))
    return pts


def test_centerline_builds_closed_ring() -> None:
    spec = TrackSpec(name="rect", width=1.0, resolution=0.05, centerline=_rect_points())
    track = build_track(spec)
    assert track.track_length == pytest.approx(28.0, rel=0.01)
    x, y, _ = track.start_pose
    assert not track.point_in_wall(x, y)


def test_centerline_track_walls_closed_and_width_configured() -> None:
    spec = TrackSpec(name="rect", width=1.0, resolution=0.05, centerline=_rect_points())
    track = build_track(spec)
    cl = track.centerline[:, :2]
    for wall in (track.left_wall, track.right_wall):
        assert wall.shape == (len(cl), 2)
        assert np.allclose(wall[0], wall[-1])
    assert track.width == pytest.approx(1.0, abs=0.05)


def _explicit_wall_track() -> tuple[TrackSpec, tuple[np.ndarray, np.ndarray]]:
    spec = TrackSpec(
        name="explicit", width=1.0, resolution=0.05, centerline=_rect_points()
    )
    # CCW ring: the inner boundary sits on the left, the outer on the right.
    left_wall = _rect_ring(0.5, 0.5, 9.5, 3.5, 0.1)
    right_wall = _rect_ring(-0.5, -0.5, 10.5, 4.5, 0.1)
    return spec, (left_wall, right_wall)


def test_explicit_walls_and_grid_pass_through() -> None:
    spec, walls = _explicit_wall_track()
    grid = ((-1.0, -1.0), (120, 60), np.zeros((120, 60), dtype=bool))
    track = build_track(spec, walls=walls, grid=grid)
    left_wall, right_wall = walls
    assert np.array_equal(track.left_wall, left_wall)
    assert np.array_equal(track.right_wall, right_wall)
    assert np.array_equal(track.occupied, grid[2])
    assert track.grid_origin == grid[0]
    assert track.grid_shape == grid[1]
    # The ring is 1.0 m wide on the straights, so the median wall-to-wall
    # distance is 1.0 (corner samples sit slightly wider and are outvoted).
    assert track.width == pytest.approx(1.0, abs=0.01)


def test_explicit_walls_require_explicit_grid() -> None:
    spec, walls = _explicit_wall_track()
    with pytest.raises(TrackError, match="explicit grid"):
        build_track(spec, walls=walls)


def test_explicit_walls_must_close() -> None:
    spec, (_, right_wall) = _explicit_wall_track()
    grid = ((-1.0, -1.0), (120, 60), np.zeros((120, 60), dtype=bool))
    open_wall = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
    with pytest.raises(TrackError, match="does not close"):
        build_track(spec, walls=(open_wall, right_wall), grid=grid)


def _rect_ring(x0: float, y0: float, x1: float, y1: float, step: float) -> np.ndarray:
    xb = np.arange(x0, x1 + step / 2, step)
    yt = np.arange(x1, x0 - step / 2, -step)
    yb = np.arange(y0, y1 + step / 2, step)
    yl = np.arange(y1, y0 - step / 2, -step)
    ring = np.vstack(
        [
            np.column_stack([xb, np.full_like(xb, y0)]),
            np.column_stack([np.full_like(yb, x1), yb]),
            np.column_stack([yt, np.full_like(yt, y1)]),
            np.column_stack([np.full_like(yl, x0), yl]),
        ]
    )
    return np.vstack([ring, ring[:1]])


def test_centerline_rejects_open_ring() -> None:
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (0.0, 4.0)]
    spec = TrackSpec(name="open", width=1.0, resolution=0.1, centerline=pts)
    with pytest.raises(TrackError, match="does not close"):
        build_track(spec)


def test_centerline_rejects_too_few_points() -> None:
    spec = TrackSpec(
        name="tiny", width=1.0, resolution=0.1, centerline=[(0.0, 0.0), (1.0, 0.0)]
    )
    with pytest.raises(TrackError, match="at least 4"):
        build_track(spec)


def test_build_track_without_layout() -> None:
    spec = TrackSpec(name="empty", width=1.0, resolution=0.1)
    with pytest.raises(TrackError, match="no layout"):
        build_track(spec)
