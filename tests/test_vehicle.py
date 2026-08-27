"""Tests for the per-vehicle record: centerline position and crash."""

from collections.abc import Callable

import numpy as np
import pytest

from cocoracer.controller import Controller
from cocoracer.lap_tracker import LapTracker
from cocoracer.race_state import DnfReason, RaceState, VehicleStatus
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


def _vehicle(track: Track, max_crashes: int = 5) -> Vehicle:
    return Vehicle(
        name="v",
        controller=_Still(),
        state=RaceState(
            pause_ticks=20, ghost_ticks=60, max_crashes=max_crashes, laps_target=3
        ),
        tracker=LapTracker(track.track_length, track.checkpoint_s),
    )


def test_vehicle_defaults_to_still_at_origin(stadium: Track) -> None:
    v = _vehicle(stadium)
    assert v.state.status is VehicleStatus.RACING
    assert (v.x, v.y, v.yaw, v.speed, v.steering) == (0.0, 0.0, 0.0, 0.0, 0.0)
    assert (v.target_speed, v.target_steering) == (0.0, 0.0)


def test_vehicle_records_fields(stadium: Track) -> None:
    v = _vehicle(stadium)
    v.x, v.y, v.yaw = 1.0, 2.0, 0.5
    v.speed, v.steering = 3.0, -0.1
    v.target_speed, v.target_steering = 4.0, 0.2
    assert (v.x, v.y, v.yaw) == (1.0, 2.0, 0.5)
    assert (v.speed, v.steering, v.target_speed, v.target_steering) == (
        3.0,
        -0.1,
        4.0,
        0.2,
    )


def _pose_at(v: Vehicle, track: Track, s: float) -> None:
    v.x, v.y, v.yaw = track.to_cartesian(s, 0.0)


def test_anchor_then_record_books_a_lap_timed_from_the_anchor(
    stadium: Track,
) -> None:
    v = _vehicle(stadium)
    v.x, v.y, v.yaw = stadium.start_pose
    v.anchor(stadium, 10.0)
    steps = 24
    for i in range(1, steps + 1):
        s = (i / steps) * stadium.track_length % stadium.track_length
        _pose_at(v, stadium, s)
        v.record(stadium, 10.0 + i * 0.5)
    assert v.state.laps_completed == 1
    assert v.state.last_lap == pytest.approx(12.0)


def test_record_does_not_feed_a_non_racing_vehicle(stadium: Track) -> None:
    v = _vehicle(stadium)
    v.x, v.y, v.yaw = stadium.start_pose
    v.anchor(stadium, 0.0)
    length = stadium.track_length
    for i in range(1, 13):
        _pose_at(v, stadium, (i / 24) * length)
        v.record(stadium, i * 0.5)
    # The checkpoint crossing is latched. Now ghost the car and jump it
    # across the start/finish line: if record fed the ghost, the jump
    # would arm a lap for the next racing feed.
    v.state.status = VehicleStatus.GHOST
    _pose_at(v, stadium, length - 1.0)
    v.record(stadium, 7.0)
    v.state.status = VehicleStatus.RACING
    _pose_at(v, stadium, 1.0)
    v.record(stadium, 8.0)
    assert v.state.laps_completed == 0


def _walled_track(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> Track:
    occupied = np.zeros((21, 21), dtype=bool)
    occupied[:, 11:] = True
    return synthetic_track_factory(occupied)


def test_crash_zeroes_motion_and_resets_to_centerline(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    v = _vehicle(track)
    v.x, v.y, v.yaw = 1.5, 1.0, 0.0
    v.speed, v.steering = 3.0, -0.2
    v.target_speed, v.target_steering = 4.0, 0.3
    dnf = v.crash(track)
    assert dnf is False
    assert v.state.status is VehicleStatus.PAUSED
    assert v.state.crashes == 1
    assert (v.speed, v.steering, v.target_speed, v.target_steering) == (
        0.0,
        0.0,
        0.0,
        0.0,
    )
    assert v.x == pytest.approx(0.0, abs=1e-9)
    assert v.y == pytest.approx(0.0, abs=1e-9)


def test_crash_at_crash_limit_dnfs_and_skips_the_reset(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    v = _vehicle(track, max_crashes=1)
    v.x, v.y, v.yaw = 1.5, 1.0, 0.0
    dnf = v.crash(track)
    assert dnf is True
    assert v.state.status is VehicleStatus.DNF
    assert v.state.dnf_reason is DnfReason.MAX_CRASHES
    assert (v.x, v.y, v.yaw) == (1.5, 1.0, 0.0)
    assert (v.speed, v.steering, v.target_speed, v.target_steering) == (
        0.0,
        0.0,
        0.0,
        0.0,
    )
