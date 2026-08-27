"""Engine-seam tests for the deterministic headless race engine."""

import dataclasses
import math
from pathlib import Path

import pytest

from cocoracer.config import Config
from cocoracer.controller import Controller, TrackInfo, load_controller
from cocoracer.engine import DnfReason, RaceEngine, RaceResult, VehicleStatus, run_race
from cocoracer.track import Track


class StraightDriver(Controller):
    """Commands a constant forward speed with zero steering."""

    def __init__(self, speed: float) -> None:
        self._speed = speed

    def step(
        self, x: float, y: float, yaw: float, speed: float, steering_angle: float
    ) -> tuple[float, float]:
        return self._speed, 0.0


def test_straight_car_stays_on_straight(stadium: Track, config: Config) -> None:
    engine = RaceEngine(stadium, config, [StraightDriver(2.0)])
    for _ in range(100):
        engine.tick()
    v = engine.vehicles[0]
    assert v.status is VehicleStatus.RACING
    assert v.crashes == 0
    assert v.y == pytest.approx(0.0, abs=1e-3)
    assert v.yaw == pytest.approx(0.0, abs=1e-3)
    assert v.x == pytest.approx(4.75, rel=0.02)


def test_crash_resets_to_centerline_then_pause_and_ghost(
    stadium: Track, config: Config
) -> None:
    engine = RaceEngine(stadium, config, [StraightDriver(2.0)], ["crasher"])
    v = engine.vehicles[0]
    while v.status is VehicleStatus.RACING:
        engine.tick()
    assert v.status is VehicleStatus.PAUSED
    assert v.crashes == 1
    assert v.speed == 0.0
    assert v.steering == 0.0
    assert v.target_speed == 0.0
    assert v.target_steering == 0.0
    _, lateral, _ = stadium.to_frenet(v.x, v.y, v.yaw)
    assert abs(lateral) < 1e-4
    statuses: list[VehicleStatus] = []
    for _ in range(81):
        engine.tick()
        statuses.append(v.status)
    assert statuses[:19] == [VehicleStatus.PAUSED] * 19
    assert statuses[19:79] == [VehicleStatus.GHOST] * 60
    assert statuses[79] is VehicleStatus.RACING


class ShuttleDriver(Controller):
    """Oscillates across the start line without ever going through the
    track, so forward start-line crossings happen without the checkpoint.

    A 10-tick pre-roll at +2 m/s (exactly reaching +2 m/s) hands off to
    alternating 30-tick phases at +/-2 m/s. A full sign flip takes
    0.5 s = 20 ticks, so each phase ends exactly at the opposite speed
    and the motion is periodic: x swings between -0.75 and +0.75 m,
    crossing the start line both ways every cycle.
    """

    def __init__(self, pre_ticks: int, phase_ticks: int, speed: float) -> None:
        self._pre = pre_ticks
        self._phase = phase_ticks
        self._speed = speed
        self._tick = 0

    def step(
        self, x: float, y: float, yaw: float, speed: float, steering_angle: float
    ) -> tuple[float, float]:
        if self._tick < self._pre:
            target = self._speed
        else:
            index = (self._tick - self._pre) // self._phase
            target = self._speed if index % 2 == 1 else -self._speed
        self._tick += 1
        return target, 0.0


def test_oscillation_across_start_line_books_no_lap(
    stadium: Track, config: Config
) -> None:
    config = dataclasses.replace(
        config, vehicle=dataclasses.replace(config.vehicle, min_speed=-2.0)
    )
    engine = RaceEngine(stadium, config, [ShuttleDriver(10, 30, 2.0)], ["shuttle"])
    v = engine.vehicles[0]
    max_x, min_x = v.x, v.x
    for _ in range(400):
        engine.tick()
        max_x = max(max_x, v.x)
        min_x = min(min_x, v.x)
    assert v.status is VehicleStatus.RACING
    assert v.crashes == 0
    assert max_x > 0.3
    assert min_x < -0.3
    assert v.laps_completed == 0
    assert v.best_lap is None


class StadiumDriver(Controller):
    """Follows the stadium centerline: straight at zero steering, steady
    turn steering (radius 2.0, wheelbase 0.3302) in both 180-degree arcs."""

    ARC_STEER = 0.16368

    def __init__(self, speed: float) -> None:
        self._speed = speed
        self._s = 0.0
        self._length = 24.5664

    def reset(self, track_info: TrackInfo) -> None:
        self._s = 0.0
        self._length = track_info.track_length

    def step(
        self, x: float, y: float, yaw: float, speed: float, steering_angle: float
    ) -> tuple[float, float]:
        self._s = (self._s + speed * 0.025) % self._length
        s = self._s
        in_arc = (6.0 <= s < 6.0 + 2.0 * math.pi) or (
            12.0 + 2.0 * math.pi <= s < self._length
        )
        return self._speed, (self.ARC_STEER if in_arc else 0.0)


def test_scripted_driver_completes_a_lap(stadium: Track, config: Config) -> None:
    config = dataclasses.replace(config, race=dataclasses.replace(config.race, laps=1))
    result = run_race(stadium, config, [StadiumDriver(2.0)], ["runner"])
    r = result.results[0]
    assert r.status is VehicleStatus.FINISHED
    assert r.finish_order == 1
    assert r.laps_completed == 1
    assert r.crashes == 0
    assert r.total_time == pytest.approx(12.4, abs=0.5)
    assert r.best_lap == r.total_time
    assert r.last_lap == r.total_time
    assert r.dnf_reason is None


def test_timeout_dnfs_inactive_car(stadium: Track, config: Config) -> None:
    config = dataclasses.replace(
        config, race=dataclasses.replace(config.race, time_limit=1.0)
    )
    result = run_race(stadium, config, [StraightDriver(0.0)], ["sitter"])
    r = result.results[0]
    assert r.status is VehicleStatus.DNF
    assert r.dnf_reason is DnfReason.TIMEOUT
    assert r.finish_order is None
    assert 1.0 <= result.time < 1.05


def test_max_crashes_dnfs(stadium: Track, config: Config) -> None:
    config = dataclasses.replace(
        config, race=dataclasses.replace(config.race, max_crashes=2)
    )
    result = run_race(stadium, config, [StraightDriver(2.0)], ["crasher"])
    r = result.results[0]
    assert r.status is VehicleStatus.DNF
    assert r.dnf_reason is DnfReason.MAX_CRASHES
    assert r.crashes == 2


def _fingerprint(result: RaceResult) -> tuple:
    return (
        result.track_name,
        round(result.time, 9),
        tuple(
            (
                r.name,
                r.status,
                r.finish_order,
                r.laps_completed,
                r.crashes,
                r.dnf_reason,
                round(r.total_time or 0.0, 9),
                round(r.best_lap or 0.0, 9),
                round(r.last_lap or 0.0, 9),
            )
            for r in result.results
        ),
    )


def test_race_is_deterministic(stadium: Track, config: Config) -> None:
    first = run_race(
        stadium, config, [StadiumDriver(2.0), StraightDriver(2.0)], ["a", "b"]
    )
    second = run_race(
        stadium, config, [StadiumDriver(2.0), StraightDriver(2.0)], ["a", "b"]
    )
    assert _fingerprint(first) == _fingerprint(second)


def test_open_loop_stub_crashes_out(stadium: Track, config: Config) -> None:
    stub = Path(__file__).resolve().parent.parent / "controllers" / "open_loop.py"
    controller = load_controller(stub)
    result = run_race(stadium, config, [controller])
    r = result.results[0]
    assert r.status is VehicleStatus.DNF
    assert r.dnf_reason is DnfReason.MAX_CRASHES
    assert r.crashes == config.race.max_crashes
    assert r.laps_completed == 0
