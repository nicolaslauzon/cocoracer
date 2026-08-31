"""Traffic tests: multi-vehicle crashes, ghosts in a pack, scan
visibility, and determinism with N vehicles."""

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from cocoracer.cli import main
from cocoracer.config import Config
from cocoracer.controller import Controller
from cocoracer.engine import RaceEngine, VehicleStatus
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


@pytest.mark.slow
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
    # The chaser sits just inside the collision distance of the phantom and
    # well clear of the racer, so the first crash pairs only the chaser with
    # the phantom. The racer, behind both, then drives through the parked
    # ghosts while they hold their poses.
    engine = RaceEngine(
        stadium,
        _no_countdown(config),
        [StraightDriver(5.0), StraightDriver(0.0), StraightDriver(5.0)],
        ["chaser", "phantom", "racer"],
        mode="race",
    )
    chaser, phantom, racer = engine.vehicles
    chaser.x, chaser.y, chaser.yaw = 12.0, 0.0, 0.0
    phantom.x, phantom.y, phantom.yaw = 14.0, 0.0, 0.0
    # Far enough back that the racer reaches the parked pair during the
    # ghost window, not while they are paused (pause = 2 s = 10 m at 5 m/s).
    racer.x, racer.y, racer.yaw = 2.0, 0.0, 0.0
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
    # Every vehicle sits outside its neighbours' collision circles (radius
    # = collision distance, 2.5 m) so beam 0 sees the near side of each.
    observer.x, observer.y, observer.yaw = 3.0, 0.0, 0.0
    other.x, other.y, other.yaw = 9.0, 0.0, 0.0
    third.x, third.y, third.yaw = 13.0, 0.0, 0.0
    engine.tick()
    # Beam 0 points straight ahead: other's collision circle (radius 2.5 m,
    # center 9.0 m ahead) is 3.5 m along it, closer than third's circle and
    # far closer than the wall at the end of the straight.
    assert recorder.scans[-1][0] == pytest.approx(3.5, abs=0.05)
    # Flip the other vehicle to ghost for one tick; its timer then
    # expires on its own and the vehicle returns to racing.
    other.state.status = VehicleStatus.GHOST
    engine.tick()
    # The ghost is absent from the scan: beam 0 now sees the racing
    # third vehicle's circle 7.5 m ahead, not the ghost at 3.5 m.
    assert recorder.scans[-1][0] == pytest.approx(7.5, abs=0.05)
