"""Traffic tests: multi-vehicle crashes, ghosts in a pack, scan
visibility, and determinism with N vehicles."""

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from cocoracer.cli import main
from cocoracer.config import Config
from cocoracer.controller import Controller, load_controller
from cocoracer.engine import RaceEngine, RaceResult, VehicleStatus, run_race
from cocoracer.track import Track

REPO_ROOT = Path(__file__).resolve().parent.parent
PURE_PURSUIT = REPO_ROOT / "controllers" / "pure_pursuit.py"
OPEN_LOOP = REPO_ROOT / "controllers" / "open_loop.py"
PARAMS = REPO_ROOT / "params" / "default.yaml"


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


def test_cli_race_runs_four_controllers_headless(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(
        [
            "--params",
            str(PARAMS),
            "race",
            "--track",
            "stadium",
            "--controller",
            f"{PURE_PURSUIT},{PURE_PURSUIT},{PURE_PURSUIT},{OPEN_LOOP}",
            "--no-web",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "results (stadium):" in out
    results = out.split("results (stadium):", 1)[1]
    for name in ("pure_pursuit (1)", "pure_pursuit (2)", "pure_pursuit (3)"):
        line = next(line for line in results.splitlines() if name in line)
        assert "FINISHED" in line
        assert "3 laps" in line
    line = next(line for line in results.splitlines() if "open_loop" in line)
    assert "DNF" in line
    assert "[max crashes]" in line
    assert "race time:" in out


def _no_countdown(config: Config) -> Config:
    return dataclasses.replace(
        config, race=dataclasses.replace(config.race, countdown=0.0)
    )


def test_collision_in_traffic_resets_to_centerline(
    stadium: Track, config: Config
) -> None:
    engine = RaceEngine(
        stadium,
        _no_countdown(config),
        [StraightDriver(2.0), StraightDriver(0.0), StraightDriver(0.0)],
        ["chaser", "target", "bystander"],
        mode="race",
    )
    chaser, target, bystander = engine.vehicles
    chaser.x, chaser.y, chaser.yaw = 2.0, 0.0, 0.0
    target.x, target.y, target.yaw = 4.0, 0.0, 0.0
    bystander.x, bystander.y, bystander.yaw = 5.5, 0.0, 0.0
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
    assert bystander.state.status is VehicleStatus.RACING
    assert bystander.state.crashes == 0
    assert (bystander.x, bystander.y, bystander.yaw) == (5.5, 0.0, 0.0)


def test_ghost_cannot_be_recollided_in_traffic(stadium: Track, config: Config) -> None:
    engine = RaceEngine(
        stadium,
        _no_countdown(config),
        [StraightDriver(2.0), StraightDriver(0.0), StraightDriver(2.0)],
        ["chaser", "phantom", "racer"],
        mode="race",
    )
    chaser, phantom, racer = engine.vehicles
    chaser.x, chaser.y, chaser.yaw = 2.0, 0.0, 0.0
    phantom.x, phantom.y, phantom.yaw = 4.0, 0.0, 0.0
    racer.x, racer.y, racer.yaw = 0.0, 0.0, 0.0
    while chaser.state.is_racing or phantom.state.is_racing:
        engine.tick()
    while chaser.state.status is VehicleStatus.PAUSED:
        engine.tick()
    assert chaser.state.status is VehicleStatus.GHOST
    assert phantom.state.status is VehicleStatus.GHOST
    assert chaser.state.crashes == 1
    assert phantom.state.crashes == 1
    # The racer drives straight through the parked phantom's pose;
    # ghosts neither hit nor are hit, so nobody's crash count moves.
    min_gap = math.inf
    while racer.x < phantom.x + 0.6:
        engine.tick()
        min_gap = min(min_gap, math.hypot(racer.x - phantom.x, racer.y - phantom.y))
    assert min_gap < config.race.collision_distance
    assert phantom.state.status is VehicleStatus.GHOST
    assert phantom.state.crashes == 1
    assert chaser.state.crashes == 1
    assert racer.state.status is VehicleStatus.RACING
    assert racer.state.crashes == 0


def test_racing_visible_in_scans_ghosts_absent(stadium: Track, config: Config) -> None:
    recorder = ScanRecorder()
    engine = RaceEngine(
        stadium,
        config,
        [recorder, StraightDriver(0.0), StraightDriver(0.0)],
        ["observer", "other", "third"],
    )
    observer, other, third = engine.vehicles
    observer.x, observer.y, observer.yaw = 1.0, 0.0, 0.0
    other.x, other.y, other.yaw = 2.0, 0.0, 0.0
    third.x, third.y, third.yaw = 3.0, 0.0, 0.0
    engine.tick()
    # Beam 0 points straight ahead: other's collision circle (radius
    # 0.5 m, center 2.0 m ahead) is 0.5 m along it, far closer than the
    # wall at the end of the straight.
    assert recorder.scans[-1][0] == pytest.approx(0.5, abs=0.05)
    # Flip the other vehicle to ghost for one tick; its timer then
    # expires on its own and the vehicle returns to racing.
    other.state.status = VehicleStatus.GHOST
    engine.tick()
    # The ghost is absent from the scan: beam 0 now sees the racing
    # third vehicle's circle 1.5 m ahead, not the ghost at 0.5 m.
    assert recorder.scans[-1][0] == pytest.approx(1.5, abs=0.05)


def _load_pure_pursuit(config: Config) -> Controller:
    return load_controller(PURE_PURSUIT, baselines=config.baselines)


def test_race_is_deterministic_with_eight_vehicles(
    stadium: Track, config: Config
) -> None:
    def race() -> RaceResult:
        return run_race(
            stadium,
            config,
            [_load_pure_pursuit(config) for _ in range(8)],
            [f"v{i}" for i in range(8)],
            mode="race",
        )

    first = race()
    second = race()
    assert first.track_name == second.track_name
    assert first.time == pytest.approx(second.time, abs=1e-9)
    assert len(first.results) == 8
    for a, b in zip(first.results, second.results, strict=True):
        assert a.name == b.name
        assert a.status == b.status
        assert a.finish_order == b.finish_order
        assert a.laps_completed == b.laps_completed
        assert a.crashes == b.crashes
        assert a.dnf_reason == b.dnf_reason
        if a.total_time is None:
            assert b.total_time is None
        else:
            assert a.total_time == pytest.approx(b.total_time, abs=1e-9)
