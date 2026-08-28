"""Tests for the fleet laser scan: visibility policy and first-hit merge."""

import math
from collections.abc import Callable

import numpy as np
import pytest

from cocoracer.config import Config
from cocoracer.controller import Controller
from cocoracer.lap_tracker import LapTracker
from cocoracer.race_state import RaceState, VehicleStatus
from cocoracer.sensor import fleet_scan
from cocoracer.track import Track
from cocoracer.vehicle import Vehicle


class _Still(Controller):
    """Commands zero speed and zero steering."""

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        return 0.0, 0.0


def _angles(count: int) -> np.ndarray:
    return np.arange(count) * (2.0 * np.pi / count)


def _vehicle(
    track: Track,
    x: float,
    y: float,
    yaw: float = 0.0,
    status: VehicleStatus = VehicleStatus.RACING,
) -> Vehicle:
    v = Vehicle(
        name="v",
        controller=_Still(),
        state=RaceState(pause_ticks=20, ghost_ticks=60, max_crashes=5, laps_target=3),
        tracker=LapTracker(track.track_length, track.checkpoint_s),
        x=x,
        y=y,
        yaw=yaw,
    )
    v.state.status = status
    return v


def test_fleet_scan_reads_wall(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = synthetic_track_factory(occupied)
    scan = fleet_scan(track, [_vehicle(track, 0.0, 1.0)], _angles(72), 0.5)
    assert scan[0, 0] == pytest.approx(1.1, abs=0.15)


def test_fleet_scan_row_per_vehicle_in_fleet_order(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = synthetic_track_factory(occupied)
    a = _vehicle(track, 0.0, 0.3)
    b = _vehicle(track, 0.0, 1.7)
    scan = fleet_scan(track, [a, b], _angles(72), 0.5)
    assert scan.shape == (2, 72)
    assert scan[0, 0] == pytest.approx(1.1, abs=0.15)
    assert scan[1, 0] == pytest.approx(1.1, abs=0.15)
    # Each vehicle's beam aimed at the other (beam 18 is +y, beam 54 is
    # -y) reads the collision circle at 1.4 - 0.5, not the wall.
    assert scan[0, 18] == pytest.approx(0.9, abs=1e-6)
    assert scan[1, 54] == pytest.approx(0.9, abs=1e-6)


def test_fleet_scan_no_hit_beam_reads_inf(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    track = synthetic_track_factory(occupied)
    scan = fleet_scan(track, [_vehicle(track, 1.0, 1.0)], _angles(72), 0.5)
    assert np.all(np.isinf(scan))


def test_first_hit_wins_when_vehicle_is_nearer(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = synthetic_track_factory(occupied)
    scan = fleet_scan(
        track, [_vehicle(track, 0.0, 1.0), _vehicle(track, 0.9, 1.0)], _angles(72), 0.5
    )
    assert scan[0, 0] == pytest.approx(0.4, abs=1e-6)


def test_first_hit_wins_when_wall_is_nearer(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    track = synthetic_track_factory(occupied)
    scan = fleet_scan(
        track, [_vehicle(track, 0.0, 1.0), _vehicle(track, 2.0, 1.0)], _angles(72), 0.5
    )
    assert scan[0, 0] == pytest.approx(1.1, abs=0.15)


def test_scan_reads_wall_at_half_track_width(stadium: Track, config: Config) -> None:
    scan = fleet_scan(
        stadium,
        [_vehicle(stadium, 3.0, 0.0)],
        config.sensor.beam_angles,
        config.race.collision_distance,
    )
    b = config.sensor.beam_count
    tol = 1.5 * stadium.resolution
    assert scan[0, b // 4] == pytest.approx(stadium.half_width, abs=tol)
    assert scan[0, 3 * b // 4] == pytest.approx(stadium.half_width, abs=tol)


def test_racing_vehicle_appears_in_scan_at_correct_distance(
    stadium: Track, config: Config
) -> None:
    scanner = _vehicle(stadium, 3.0, 0.0)
    target = _vehicle(stadium, 9.0, 0.0)
    scans = fleet_scan(
        stadium,
        [scanner, target],
        config.sensor.beam_angles,
        config.race.collision_distance,
    )
    # 6 m apart (more than the collision radius), so each beam aimed at the
    # other reads the near side of the collision circle at 6 - r, well
    # before the wall.
    expected = 6.0 - config.race.collision_distance
    assert scans[0, 0] == pytest.approx(expected, abs=1e-6)
    assert scans[1, 36] == pytest.approx(expected, abs=1e-6)


def test_vehicle_never_sees_itself(stadium: Track, config: Config) -> None:
    scan = fleet_scan(
        stadium,
        [_vehicle(stadium, 5.0, 0.0)],
        config.sensor.beam_angles,
        config.race.collision_distance,
    )
    # With no other vehicle, the backward beam reads the wall well behind
    # the vehicle instead of the vehicle's own collision circle, whose far
    # side sits one radius (the collision distance) back from its center.
    assert math.isfinite(scan[0, 36])
    assert scan[0, 36] > config.race.collision_distance


def test_ghost_vehicle_is_absent_from_scan(stadium: Track, config: Config) -> None:
    scanner = _vehicle(stadium, 3.0, 0.0)
    ghost = _vehicle(stadium, 9.0, 0.0, status=VehicleStatus.GHOST)
    scans = fleet_scan(
        stadium,
        [scanner, ghost],
        config.sensor.beam_angles,
        config.race.collision_distance,
    )
    # If the ghost were visible, beam 0 would read the near side of its
    # collision circle at 6 - r; it reads the wall past the ghost instead.
    assert scans[0, 0] > 6.0 - config.race.collision_distance
    assert math.isfinite(scans[0, 0])


def test_paused_vehicle_is_absent_from_scan(stadium: Track, config: Config) -> None:
    scanner = _vehicle(stadium, 3.0, 0.0)
    pauser = _vehicle(stadium, 9.0, 0.0, status=VehicleStatus.PAUSED)
    scans = fleet_scan(
        stadium,
        [scanner, pauser],
        config.sensor.beam_angles,
        config.race.collision_distance,
    )
    # A paused vehicle is invisible: beam 0 reads the wall past it, not the
    # near side of its collision circle at 6 - r.
    assert scans[0, 0] > 6.0 - config.race.collision_distance
    assert math.isfinite(scans[0, 0])
