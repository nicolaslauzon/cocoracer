"""Direct geometry tests for the wall laser scan."""

import numpy as np
import pytest
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

from cocoracer.sensor import scan_walls
from cocoracer.track import Track


def _synthetic_track(occupied: np.ndarray, resolution: float = 0.1) -> Track:
    ny, nx = occupied.shape
    spline = CubicSpline([0.0, 1.0], [0.0, 1.0])
    return Track(
        name="synthetic",
        half_width=0.5,
        resolution=resolution,
        track_length=10.0,
        centerline=np.zeros((2, 3)),
        spline_x=spline,
        spline_y=spline,
        grid_origin=(0.0, 0.0),
        grid_shape=(ny, nx),
        occupied=occupied,
        frenet_tree=cKDTree(np.zeros((1, 2))),
        frenet_s=np.zeros(1),
    )


def _angles(count: int) -> np.ndarray:
    return np.arange(count) * (2.0 * np.pi / count)


def test_beam_reads_known_wall_distance() -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = _synthetic_track(occupied)
    scan = scan_walls(track, np.array([[0.0, 1.0, 0.0]]), _angles(72))
    # Grid-sampled hits land within ~1.5 resolutions of the true wall face:
    # occupancy is judged at cell centers, so the first occupied sample can
    # sit one full step past the face.
    assert scan[0, 0] == pytest.approx(1.1, abs=0.15)


def test_first_obstacle_wins() -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 5:7] = True
    occupied[:, 12:14] = True
    track = _synthetic_track(occupied)
    scan = scan_walls(track, np.array([[0.0, 1.0, 0.0]]), _angles(72))
    assert scan[0, 0] == pytest.approx(0.5, abs=0.15)


def test_no_hit_beam_reads_inf() -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    track = _synthetic_track(occupied)
    scan = scan_walls(track, np.array([[1.0, 1.0, 0.0]]), _angles(72))
    assert np.all(np.isinf(scan))


def test_beams_hit_only_the_wall_that_is_there() -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[15:, :] = True
    track = _synthetic_track(occupied)
    scan = scan_walls(track, np.array([[1.0, 0.05, 0.0]]), _angles(72))
    assert scan[0, 18] == pytest.approx(1.5, abs=0.15)
    assert np.isinf(scan[0, 0])
    assert np.isinf(scan[0, 54])


def test_multiple_vehicles_in_one_call() -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = _synthetic_track(occupied)
    poses = np.array([[0.0, 1.0, 0.0], [0.0, 1.0, np.pi]])
    scan = scan_walls(track, poses, _angles(72))
    assert scan.shape == (2, 72)
    assert scan[0, 0] == pytest.approx(1.1, abs=0.15)
    assert np.isinf(scan[1, 0])
    assert scan[1, 36] == pytest.approx(1.1, abs=0.15)
