"""Engine-seam tests for the deterministic headless race engine."""

import dataclasses
import math
import time
from pathlib import Path

import numpy as np
import pytest

from cocoracer.config import Config
from cocoracer.controller import Controller, TrackInfo, load_controller
from cocoracer.engine import (
    DnfReason,
    RaceEngine,
    RaceResult,
    Vehicle,
    VehicleStatus,
    run_race,
)
from cocoracer.track import Track


class StraightDriver(Controller):
    """Commands a constant forward speed with zero steering."""

    def __init__(self, speed: float) -> None:
        self._speed = speed

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        return self._speed, 0.0


def test_straight_car_stays_on_straight(stadium: Track, config: Config) -> None:
    engine = RaceEngine(stadium, config, [StraightDriver(2.0)])
    for _ in range(100):
        engine.tick()
    v = engine.vehicles[0]
    assert v.state.status is VehicleStatus.RACING
    assert v.state.crashes == 0
    assert v.y == pytest.approx(0.0, abs=1e-3)
    assert v.yaw == pytest.approx(0.0, abs=1e-3)
    assert v.x == pytest.approx(4.75, rel=0.02)


class ScanRecorder(Controller):
    """Records every laser scan it receives; drives at a fixed speed."""

    def __init__(self, speed: float = 0.0) -> None:
        self._speed = speed
        self.scans: list[np.ndarray] = []

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        self.scans.append(np.array(laser_scan))
        return self._speed, 0.0


def test_scan_arrives_every_tick_while_steppable(
    stadium: Track, config: Config
) -> None:
    recorder = ScanRecorder(25.0)
    engine = RaceEngine(stadium, config, [recorder], ["scanner"])
    v = engine.vehicles[0]
    statuses: list[VehicleStatus] = []
    for _ in range(600):
        if v.state.may_step:
            statuses.append(v.state.status)
        engine.tick()
    assert len(recorder.scans) == len(statuses)
    assert all(s.shape == (config.sensor.beam_count,) for s in recorder.scans)
    assert VehicleStatus.RACING in statuses
    assert VehicleStatus.GHOST in statuses
    assert VehicleStatus.PAUSED not in statuses


def test_tick_cost_with_eight_vehicles_stays_under_budget(
    stadium: Track, config: Config
) -> None:
    engine = RaceEngine(
        stadium,
        config,
        [ScanRecorder(0.0) for _ in range(8)],
        [f"v{i}" for i in range(8)],
    )
    for i, v in enumerate(engine.vehicles):
        v.x = 0.3 + 0.4 * i
    engine.tick()
    ticks = 20
    start = time.perf_counter()
    for _ in range(ticks):
        engine.tick()
    per_tick = (time.perf_counter() - start) / ticks
    assert per_tick < config.sim.tick_dt


def test_crash_resets_to_centerline_then_pause_and_ghost(
    stadium: Track, config: Config
) -> None:
    engine = RaceEngine(stadium, config, [StraightDriver(25.0)], ["crasher"])
    v = engine.vehicles[0]
    while v.state.status is VehicleStatus.RACING:
        engine.tick()
    assert v.state.status is VehicleStatus.PAUSED
    assert v.state.crashes == 1
    assert v.speed == 0.0
    assert v.steering == 0.0
    assert v.target_speed == 0.0
    assert v.target_steering == 0.0
    _, lateral, _ = stadium.to_frenet(v.x, v.y, v.yaw)
    assert abs(lateral) < 1e-4
    _reposition_to_wall(v)
    statuses: list[VehicleStatus] = []
    for _ in range(81):
        engine.tick()
        statuses.append(v.state.status)
    assert statuses[:19] == [VehicleStatus.PAUSED] * 19
    assert statuses[19:79] == [VehicleStatus.GHOST] * 60
    # The ghost drove through the wall, so it re-crashes the moment it
    # returns to racing.
    assert statuses[79] is VehicleStatus.PAUSED
    assert v.state.crashes == 2


def _drive_to_ghost(engine: RaceEngine, vehicle: Vehicle) -> None:
    while vehicle.state.status is VehicleStatus.RACING:
        engine.tick()
    while vehicle.state.status is VehicleStatus.PAUSED:
        engine.tick()


def test_ghost_keeps_driving_during_ghost_phase(stadium: Track, config: Config) -> None:
    engine = RaceEngine(stadium, config, [StraightDriver(25.0)], ["ghost"])
    v = engine.vehicles[0]
    _drive_to_ghost(engine, v)
    assert v.state.status is VehicleStatus.GHOST
    start_x, start_y = v.x, v.y
    travelled = 0.0
    while v.state.status is VehicleStatus.GHOST:
        engine.tick()
        travelled = max(travelled, math.hypot(v.x - start_x, v.y - start_y))
    assert travelled > 1.0
    assert v.state.laps_completed == 0
    assert v.state.best_lap is None


def test_ghost_passes_through_wall_without_crashing(
    stadium: Track, config: Config
) -> None:
    engine = RaceEngine(stadium, config, [StraightDriver(25.0)], ["ghost"])
    v = engine.vehicles[0]
    _drive_to_ghost(engine, v)
    assert v.state.status is VehicleStatus.GHOST
    _reposition_to_wall(v)
    entered_wall: tuple[float, float] | None = None
    moved_through = 0.0
    while v.state.status is VehicleStatus.GHOST:
        engine.tick()
        if entered_wall is None and stadium.footprint_in_wall(
            v.x, v.y, v.yaw, config.vehicle.length, config.vehicle.width
        ):
            entered_wall = (v.x, v.y)
        if entered_wall is not None:
            moved_through = max(
                moved_through, math.hypot(v.x - entered_wall[0], v.y - entered_wall[1])
            )
    assert entered_wall is not None
    assert moved_through > 0.5
    assert v.state.status is VehicleStatus.PAUSED
    assert v.state.crashes == 2


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
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
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
    assert v.state.status is VehicleStatus.RACING
    assert v.state.crashes == 0
    assert max_x > 0.3
    assert min_x < -0.3
    assert v.state.laps_completed == 0
    assert v.state.best_lap is None


class StadiumDriver(Controller):
    """Follows the stadium centerline: straight at zero steering, steady
    turn steering (radius 40.0, wheelbase 1.65) in both 180-degree arcs.

    `s0` is the arc length the car starts at, so the driver's internal
    position stays aligned when the engine releases it from a grid pose
    behind the start line.
    """

    ARC_STEER = math.atan(1.65 / 40.0)
    _ARC = 40.0 * math.pi

    def __init__(self, speed: float, s0: float = 0.0) -> None:
        self._speed = speed
        self._s0 = s0
        self._s = 0.0
        self._length = 491.327

    def reset(self, track_info: TrackInfo) -> None:
        self._s = self._s0 % track_info.track_length
        self._length = track_info.track_length

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        self._s = (self._s + speed * 0.025) % self._length
        s = self._s
        in_arc = (120.0 <= s < 120.0 + self._ARC) or (
            240.0 + self._ARC <= s < self._length
        )
        return self._speed, (self.ARC_STEER if in_arc else 0.0)


def _reposition_to_wall(v: Vehicle) -> None:
    """Park the vehicle just inside the bottom-straight wall, heading into it.

    On the 20 m-wide stadium a crash reset lands the vehicle 10 m from any
    wall, farther than a 1.5 s ghost drive (<=9 m from rest) can cover. Park
    it 2 m off the near wall so the ghost drive carries it through the wall
    and it re-crashes the moment it returns to racing.
    """
    v.x, v.y, v.yaw = 60.0, -8.0, -math.pi / 2.0
    v.speed = 0.0
    v.steering = 0.0
    v.target_speed = 0.0
    v.target_steering = 0.0


def test_scripted_driver_completes_a_lap(stadium: Track, config: Config) -> None:
    config = dataclasses.replace(config, race=dataclasses.replace(config.race, laps=1))
    result = run_race(stadium, config, [StadiumDriver(20.0)], ["runner"])
    r = result.results[0]
    assert r.status is VehicleStatus.FINISHED
    assert r.finish_order == 1
    assert r.laps_completed == 1
    assert r.crashes == 0
    # track_length / speed plus the standing-start ramp to 20 m/s.
    assert r.total_time == pytest.approx(25.8, abs=0.5)
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
    result = run_race(stadium, config, [StraightDriver(25.0)], ["crasher"])
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
    config = dataclasses.replace(config, race=dataclasses.replace(config.race, laps=1))
    first = run_race(
        stadium, config, [StadiumDriver(25.0), StraightDriver(25.0)], ["a", "b"]
    )
    second = run_race(
        stadium, config, [StadiumDriver(25.0), StraightDriver(25.0)], ["a", "b"]
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


def test_snapshot_reports_racing_and_crashed_vehicles(
    stadium: Track, config: Config
) -> None:
    config = dataclasses.replace(
        config, race=dataclasses.replace(config.race, max_crashes=1)
    )
    engine = RaceEngine(
        stadium, config, [StraightDriver(25.0), StraightDriver(0.5)], ["fast", "slow"]
    )
    fast, slow = engine.vehicles
    # The faster car starts ahead so the two live vehicles never touch.
    fast.x = 3.0
    while fast.state.status is not VehicleStatus.DNF:
        engine.tick()
    snap = engine.snapshot()
    assert snap.time == engine.time
    assert snap.track is stadium
    assert len(snap.vehicles) == 2
    f = snap.vehicles[0]
    assert f.name == "fast"
    assert f.id == 0
    assert f.status is VehicleStatus.DNF
    assert f.crashes == 1
    assert f.dnf_reason is DnfReason.MAX_CRASHES
    assert f.x == fast.x
    assert f.y == fast.y
    assert f.yaw == fast.yaw
    assert f.speed == fast.speed
    assert f.steering == fast.steering
    assert f.laps_completed == 0
    assert f.best_lap is None
    assert f.last_lap is None
    assert f.finish_time is None
    s = snap.vehicles[1]
    assert s.name == "slow"
    assert s.id == 1
    assert s.status is VehicleStatus.RACING
    assert s.crashes == 0
    assert s.dnf_reason is None
    assert s.x == slow.x
    assert s.y == slow.y
    assert s.yaw == slow.yaw
    assert s.speed == slow.speed
    assert s.steering == slow.steering


def test_snapshot_is_a_pure_read(stadium: Track, config: Config) -> None:
    engine = RaceEngine(stadium, config, [StraightDriver(2.0)], ["reader"])
    engine.tick()
    engine.tick()
    v = engine.vehicles[0]
    before = (
        engine.time,
        v.x,
        v.y,
        v.yaw,
        v.speed,
        v.steering,
        v.state.status,
        v.state.crashes,
    )
    first = engine.snapshot()
    second = engine.snapshot()
    assert first == second
    after = (
        engine.time,
        v.x,
        v.y,
        v.yaw,
        v.speed,
        v.steering,
        v.state.status,
        v.state.crashes,
    )
    assert before == after


class StepCounter(Controller):
    """Drives at a constant speed; counts how often step is called."""

    def __init__(self, speed: float) -> None:
        self._speed = speed
        self.steps = 0

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        self.steps += 1
        return self._speed, 0.0


def test_engine_rejects_unknown_mode(stadium: Track, config: Config) -> None:
    with pytest.raises(ValueError, match="mode must be one of"):
        RaceEngine(stadium, config, [StraightDriver(2.0)], ["x"], mode="duel")


def test_engine_without_auto_start_is_waiting(stadium: Track, config: Config) -> None:
    engine = RaceEngine(stadium, config, [StepCounter(2.0)], ["idle"], auto_start=False)
    assert engine.phase == "waiting"
    assert engine.time == 0.0


def test_ticks_while_waiting_advance_nothing(stadium: Track, config: Config) -> None:
    first = StepCounter(2.0)
    engine = RaceEngine(
        stadium, config, [first], ["idle"], mode="race", auto_start=False
    )
    v = engine.vehicles[0]
    pose = (v.x, v.y, v.yaw)
    for _ in range(10):
        engine.tick()
    assert engine.time == 0.0
    assert (v.x, v.y, v.yaw) == pose
    assert v.speed == 0.0
    assert v.state.status is VehicleStatus.RACING
    assert first.steps == 0
    assert engine.countdown == pytest.approx(config.race.countdown, abs=1e-9)


def test_start_begins_countdown_in_race_mode(stadium: Track, config: Config) -> None:
    first = StepCounter(2.0)
    engine = RaceEngine(
        stadium, config, [first], ["idle"], mode="race", auto_start=False
    )
    engine.start()
    assert engine.phase == "countdown"
    countdown_ticks = int(round(config.race.countdown / config.sim.tick_dt))
    for _ in range(countdown_ticks):
        engine.tick()
    assert engine.phase == "racing"
    assert first.steps == 0
    engine.tick()
    assert first.steps == 1


def test_start_releases_immediately_in_time_trial(
    stadium: Track, config: Config
) -> None:
    first = StepCounter(2.0)
    engine = RaceEngine(stadium, config, [first], ["idle"], auto_start=False)
    assert engine.phase == "waiting"
    engine.start()
    assert engine.phase == "racing"
    engine.tick()
    assert first.steps == 1
    assert engine.time == pytest.approx(config.sim.tick_dt, abs=1e-9)


def test_auto_start_default_skips_waiting(stadium: Track, config: Config) -> None:
    trial = RaceEngine(stadium, config, [StraightDriver(2.0)], ["tt"])
    assert trial.phase == "racing"
    race = RaceEngine(stadium, config, [StraightDriver(2.0)], ["rr"], mode="race")
    assert race.phase == "countdown"
    assert race.countdown == pytest.approx(config.race.countdown, abs=1e-9)


def test_run_releases_a_waiting_engine(stadium: Track, config: Config) -> None:
    config = dataclasses.replace(
        config, race=dataclasses.replace(config.race, time_limit=1.0)
    )
    engine = RaceEngine(
        stadium, config, [StraightDriver(0.0)], ["sitter"], auto_start=False
    )
    result = engine.run()
    assert result.results[0].dnf_reason is DnfReason.TIMEOUT
    assert 1.0 <= result.time < 1.05


# The hardcoded F1 zigzag: pole on the centerline 3.75 m behind the
# line, then 2.5 m right, left, right, ... at 3.75 m rows.
_ZIGZAG_ROWS = 3.75
_ZIGZAG_LATERAL = (0.0, -2.5, 2.5, -2.5, 2.5)


def _assert_zigzag(track: Track, engine: RaceEngine) -> None:
    length = track.track_length
    for i, v in enumerate(engine.vehicles):
        s, d, dyaw = track.to_frenet(v.x, v.y, v.yaw)
        # 1 cm: the Frenet roundtrip of an off-centerline pose loses up
        # to ~2 mm of arc length on the stadium's spline arcs.
        assert s == pytest.approx((length - (i + 1) * _ZIGZAG_ROWS) % length, abs=0.01)
        assert d == pytest.approx(_ZIGZAG_LATERAL[i], abs=1e-3)
        assert abs(dyaw) < 1e-3
        assert v.speed == 0.0
        assert v.target_speed == 0.0


def test_race_mode_starts_on_zigzag_grid(stadium: Track, config: Config) -> None:
    drivers: list[Controller] = [StepCounter(2.0) for _ in range(5)]
    engine = RaceEngine(
        stadium, config, drivers, [f"v{i}" for i in range(5)], mode="race"
    )
    _assert_zigzag(stadium, engine)


def test_zigzag_grid_is_identical_on_other_tracks(
    f1_tracks: dict[str, Track], config: Config
) -> None:
    track = f1_tracks["montreal"]
    drivers: list[Controller] = [StepCounter(2.0) for _ in range(5)]
    engine = RaceEngine(
        track, config, drivers, [f"v{i}" for i in range(5)], mode="race"
    )
    _assert_zigzag(track, engine)


def test_countdown_holds_vehicles_still_and_silent(
    stadium: Track, config: Config
) -> None:
    first = StepCounter(2.0)
    second = StepCounter(2.0)
    engine = RaceEngine(stadium, config, [first, second], ["a", "b"], mode="race")
    start = [(v.x, v.y, v.yaw) for v in engine.vehicles]
    countdown_ticks = int(round(config.race.countdown / config.sim.tick_dt))
    for _ in range(countdown_ticks):
        engine.tick()
    for (x0, y0, yaw0), v in zip(start, engine.vehicles, strict=True):
        assert (v.x, v.y, v.yaw) == (x0, y0, yaw0)
        assert v.speed == 0.0
        assert v.state.status is VehicleStatus.RACING
    assert engine.time == pytest.approx(config.race.countdown, abs=1e-9)
    assert first.steps == 0 and second.steps == 0
    engine.tick()
    assert first.steps == 1 and second.steps == 1
    assert engine.vehicles[0].speed > 0.0


def test_lap_timing_starts_at_countdown_end(stadium: Track, config: Config) -> None:
    config = dataclasses.replace(config, race=dataclasses.replace(config.race, laps=1))
    grid_s = stadium.track_length - _ZIGZAG_ROWS
    result = run_race(
        stadium, config, [StadiumDriver(20.0, s0=grid_s)], ["runner"], mode="race"
    )
    r = result.results[0]
    assert r.status is VehicleStatus.FINISHED
    assert r.laps_completed == 1
    assert r.total_time is not None
    assert r.last_lap is not None
    # The lap clock starts at the release, not at the first tick:
    # finish time minus the single lap is exactly the countdown.
    assert r.total_time - r.last_lap == pytest.approx(config.race.countdown, abs=1e-9)
    # One lap is the full track plus the grid offset behind the line,
    # with the standing-start ramp (the car is released from rest) in
    # place of the first 25 m at cruise.
    speed = 20.0
    accel = config.vehicle.max_accel
    ramp_time = speed / accel
    ramp_dist = 0.5 * accel * ramp_time * ramp_time
    expected = ramp_time + (stadium.track_length + _ZIGZAG_ROWS - ramp_dist) / speed
    assert r.last_lap == pytest.approx(expected, abs=0.5)


def test_vehicle_collision_resets_both_to_pause_and_ghost(
    stadium: Track, config: Config
) -> None:
    config = dataclasses.replace(
        config, race=dataclasses.replace(config.race, countdown=0.0)
    )
    engine = RaceEngine(
        stadium,
        config,
        [StraightDriver(2.0), StraightDriver(0.0)],
        ["chaser", "target"],
        mode="race",
    )
    chaser, target = engine.vehicles
    chaser.x, chaser.y, chaser.yaw = 3.0, 0.0, 0.0
    target.x, target.y, target.yaw = 5.0, 0.0, 0.0
    while chaser.state.is_racing and target.state.is_racing:
        engine.tick()
    assert chaser.state.status is VehicleStatus.PAUSED
    assert target.state.status is VehicleStatus.PAUSED
    assert chaser.state.crashes == 1
    assert target.state.crashes == 1
    for v in (chaser, target):
        assert v.speed == 0.0
        assert v.target_speed == 0.0
        assert v.steering == 0.0
        assert v.target_steering == 0.0
        _, lateral, _ = stadium.to_frenet(v.x, v.y, v.yaw)
        assert abs(lateral) < 1e-4
    statuses: list[tuple[VehicleStatus, VehicleStatus]] = []
    for _ in range(79):
        engine.tick()
        statuses.append((chaser.state.status, target.state.status))
    # Both pause, ghost, and re-race in lockstep; ghosts cannot
    # re-collide, so the crash count does not move.
    assert all(s == (VehicleStatus.PAUSED, VehicleStatus.PAUSED) for s in statuses[:19])
    assert all(s == (VehicleStatus.GHOST, VehicleStatus.GHOST) for s in statuses[19:79])
    assert chaser.state.crashes == 1
    assert target.state.crashes == 1


def test_race_ends_on_timeout_with_dnfs_ranked_last(
    stadium: Track, config: Config
) -> None:
    config = dataclasses.replace(
        config, race=dataclasses.replace(config.race, laps=1, time_limit=30.0)
    )
    grid_s = stadium.track_length - _ZIGZAG_ROWS
    engine = RaceEngine(
        stadium,
        config,
        [StadiumDriver(20.0, s0=grid_s), StraightDriver(0.0)],
        ["fast", "sitter"],
        mode="race",
    )
    # The fast car's lap loops back through the sitter's grid spot just
    # before the finish, so a grid-placed sitter would be struck. Park it
    # off the centerline, where the following car never goes.
    sitter = engine.vehicles[1]
    sitter.x, sitter.y, sitter.yaw = 60.0, -6.0, 0.0
    sitter.speed = 0.0
    sitter.steering = 0.0
    sitter.target_speed = 0.0
    sitter.target_steering = 0.0
    result = engine.run()
    fast_res, sitter_res = result.results
    assert fast_res.status is VehicleStatus.FINISHED
    assert fast_res.finish_order == 1
    assert fast_res.total_time is not None
    assert fast_res.total_time < 30.0
    assert sitter_res.status is VehicleStatus.DNF
    assert sitter_res.dnf_reason is DnfReason.TIMEOUT
    assert sitter_res.finish_order is None
    assert 30.0 <= result.time < 30.05


def test_race_ranks_two_finishers_by_finish_time(
    stadium: Track, config: Config
) -> None:
    config = dataclasses.replace(config, race=dataclasses.replace(config.race, laps=1))
    length = stadium.track_length
    grids = [(length - (i + 1) * _ZIGZAG_ROWS) % length for i in range(2)]
    result = run_race(
        stadium,
        config,
        [StadiumDriver(15.0, s0=grids[0]), StadiumDriver(10.0, s0=grids[1])],
        ["fast", "slow"],
        mode="race",
    )
    fast, slow = result.results
    assert all(r.status is VehicleStatus.FINISHED for r in result.results)
    assert all(r.laps_completed == 1 for r in result.results)
    assert fast.dnf_reason is None and slow.dnf_reason is None
    assert fast.finish_order == 1
    assert slow.finish_order == 2
    assert fast.total_time is not None and slow.total_time is not None
    assert fast.total_time < slow.total_time
    # The race ends when the last car crosses, not at the time limit.
    assert result.time == pytest.approx(slow.total_time, abs=1e-9)
