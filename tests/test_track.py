import math
from collections.abc import Callable

import numpy as np
import pytest
from scipy.spatial import cKDTree

from cocoracer.config import Segment, TrackSpec
from cocoracer.track import Track, TrackError, build_track

F1_TRACKS = ("montreal", "spa", "silverstone")
F1_OFFICIAL_LENGTH_M = {"montreal": 4361.0, "spa": 7004.0, "silverstone": 5891.0}
F1_SCALE = 1.0 / 12.0


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


@pytest.mark.parametrize("name", F1_TRACKS)
def test_f1_track_closes(name: str, f1_tracks: dict[str, Track]) -> None:
    track = f1_tracks[name]
    assert track.track_length > 100.0
    first, last = track.centerline[0], track.centerline[-1]
    assert np.allclose([first[0], first[1]], [last[0], last[1]], atol=1e-6)
    assert abs(wrap(first[2] - last[2])) < 1e-6


@pytest.mark.parametrize("name", F1_TRACKS)
def test_f1_track_length_matches_official(
    name: str, f1_tracks: dict[str, Track]
) -> None:
    track = f1_tracks[name]
    expected = F1_OFFICIAL_LENGTH_M[name] * F1_SCALE
    assert track.track_length == pytest.approx(expected, rel=0.01)


@pytest.mark.parametrize("name", F1_TRACKS)
def test_f1_track_starts_on_straight(name: str, f1_tracks: dict[str, Track]) -> None:
    track = f1_tracks[name]
    _, _, yaw0 = track.start_pose
    _, _, yaw1 = track.to_cartesian(2.0, 0.0)
    assert abs(wrap(yaw1 - yaw0)) < math.pi / 36.0


@pytest.mark.parametrize("name", F1_TRACKS)
def test_f1_track_frenet_roundtrip(name: str, f1_tracks: dict[str, Track]) -> None:
    track = f1_tracks[name]
    for s in (
        0.0,
        1.0,
        10.0,
        50.0,
        100.0,
        track.track_length / 2.0,
        track.track_length - 0.4,
    ):
        x, y, psi = track.to_cartesian(s, 0.0)
        s2, d2, dyaw = track.to_frenet(x, y, psi)
        assert s2 == pytest.approx(s, abs=5e-3)
        assert d2 == pytest.approx(0.0, abs=5e-3)
        assert dyaw == pytest.approx(0.0, abs=5e-3)


@pytest.mark.parametrize("name", F1_TRACKS)
def test_f1_track_frenet_roundtrip_lateral(
    name: str, f1_tracks: dict[str, Track]
) -> None:
    track = f1_tracks[name]
    s, d = 5.0, 0.3
    x, y, psi = track.to_cartesian(s, d)
    s2, d2, _ = track.to_frenet(x, y, psi)
    assert s2 == pytest.approx(s, abs=5e-3)
    assert d2 == pytest.approx(d, abs=5e-3)


@pytest.mark.parametrize("name", F1_TRACKS)
def test_f1_track_grid_matches_half_width(
    name: str, f1_tracks: dict[str, Track]
) -> None:
    track = f1_tracks[name]
    ox, oy = track.grid_origin
    ny, nx = track.grid_shape
    cx = ox + (np.arange(nx) + 0.5) * track.resolution
    cy = oy + (np.arange(ny) + 0.5) * track.resolution
    gx, gy = np.meshgrid(cx, cy, indexing="xy")
    tree = cKDTree(track.centerline[:, :2])
    dist, _ = tree.query(np.column_stack([gx.ravel(), gy.ravel()]))
    expected = dist.reshape(ny, nx) > track.half_width
    assert np.array_equal(track.occupied, expected)


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


def test_centerline_builds_closed_ring() -> None:
    pts = [(float(x), 0.0) for x in np.arange(0.0, 10.1, 0.5)]
    pts += [(10.0, float(y)) for y in np.arange(0.5, 4.5, 0.5)]
    pts += [(float(x), 4.0) for x in np.arange(9.5, -0.01, -0.5)]
    pts += [(0.0, float(y)) for y in np.arange(3.5, -0.01, -0.5)]
    pts.append((0.0, 0.0))
    spec = TrackSpec(name="rect", width=1.0, resolution=0.05, centerline=pts)
    track = build_track(spec)
    assert track.track_length == pytest.approx(28.0, rel=0.01)
    x, y, _ = track.start_pose
    assert not track.point_in_wall(x, y)


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
