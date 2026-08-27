"""Tests for batched crash detection: walls, pairs, one crash per tick."""

from collections.abc import Callable

import numpy as np

from cocoracer.collision import collide
from cocoracer.controller import Controller
from cocoracer.lap_tracker import LapTracker
from cocoracer.race_state import RaceState, VehicleStatus
from cocoracer.track import Track
from cocoracer.vehicle import Vehicle

LENGTH = 0.8
WIDTH = 0.5
RADIUS = 0.5


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


def _walled_track(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> Track:
    # 3.1 m grid; the wall is the half at x >= 2.1, leaving x < 2.1 wall-free.
    occupied = np.zeros((31, 31), dtype=bool)
    occupied[:, 21:] = True
    return synthetic_track_factory(occupied)


def test_racing_car_in_wall_is_reported(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    v = _vehicle(track, 2.5, 1.5)
    assert collide(track, [v], LENGTH, WIDTH, RADIUS) == [v]


def test_ghost_and_paused_in_wall_are_not_reported(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    ghost = _vehicle(track, 2.5, 0.8, status=VehicleStatus.GHOST)
    pauser = _vehicle(track, 2.5, 2.2, status=VehicleStatus.PAUSED)
    assert collide(track, [ghost, pauser], LENGTH, WIDTH, RADIUS) == []


def test_racing_pair_below_distance_is_reported_in_fleet_order(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    a = _vehicle(track, 1.0, 1.5)
    b = _vehicle(track, 1.3, 1.5)
    assert collide(track, [a, b], LENGTH, WIDTH, RADIUS) == [a, b]


def test_racing_pair_at_or_above_distance_is_not_reported(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    a = _vehicle(track, 1.0, 1.5)
    b = _vehicle(track, 1.5, 1.5)
    assert collide(track, [a, b], LENGTH, WIDTH, RADIUS) == []


def test_overlapping_ghost_does_not_crash_the_racer(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    racer = _vehicle(track, 1.0, 1.5)
    ghost = _vehicle(track, 1.05, 1.5, status=VehicleStatus.GHOST)
    assert collide(track, [racer, ghost], LENGTH, WIDTH, RADIUS) == []


def test_overlapping_paused_does_not_crash_the_racer(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    racer = _vehicle(track, 1.0, 1.5)
    pauser = _vehicle(track, 1.05, 1.5, status=VehicleStatus.PAUSED)
    assert collide(track, [racer, pauser], LENGTH, WIDTH, RADIUS) == []


def test_wall_hits_come_before_pair_hits(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    waller = _vehicle(track, 2.5, 1.5)
    a = _vehicle(track, 1.0, 1.5)
    b = _vehicle(track, 1.3, 1.5)
    assert collide(track, [waller, a, b], LENGTH, WIDTH, RADIUS) == [
        waller,
        a,
        b,
    ]


def test_wall_hits_drop_out_of_the_pair_pass(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    track = _walled_track(synthetic_track_factory)
    # Two overlapping wall victims: the old ordering crashed each of them
    # again in the pair pass; the wall pass consumes both, so the pair
    # pass has nothing left to do.
    a = _vehicle(track, 2.5, 1.2)
    b = _vehicle(track, 2.5, 1.6)
    crashed = collide(track, [a, b], LENGTH, WIDTH, RADIUS)
    assert crashed == [a, b]
    a.crash(track)
    b.crash(track)
    assert a.state.crashes == 1
    assert b.state.crashes == 1


def test_a_vehicle_takes_at_most_one_crash_per_tick(
    synthetic_track_factory: Callable[[np.ndarray], Track],
) -> None:
    # a-b and b-c are both below RADIUS. The old snapshot ordering
    # crashed b twice in this one tick; the pair pass consumes b in the
    # (a, b) pair, so (b, c) is skipped and c survives this tick.
    track = _walled_track(synthetic_track_factory)
    a = _vehicle(track, 0.6, 1.5)
    b = _vehicle(track, 1.0, 1.5)
    c = _vehicle(track, 1.4, 1.5)
    crashed = collide(track, [a, b, c], LENGTH, WIDTH, RADIUS)
    assert crashed == [a, b]
    for v in crashed:
        v.crash(track)
    assert a.state.crashes == 1
    assert b.state.crashes == 1
    assert c.state.crashes == 0
    assert c.state.status is VehicleStatus.RACING
