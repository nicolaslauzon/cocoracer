"""Tests for the wall-follow reactive baseline (issue 14)."""

from pathlib import Path

import numpy as np
import pytest

from cocoracer.config import Config
from cocoracer.controller import (
    ControllerError,
    load_controller,
    make_track_info,
)
from cocoracer.engine import run_race
from cocoracer.race_state import VehicleStatus
from cocoracer.track import Track

REPO_ROOT = Path(__file__).resolve().parent.parent
WALL_FOLLOW = REPO_ROOT / "controllers" / "wall_follow.py"
PURE_PURSUIT = REPO_ROOT / "controllers" / "pure_pursuit.py"


def test_loader_injects_baselines(config: Config, stadium: Track) -> None:
    ctl = load_controller(WALL_FOLLOW, baselines=config.baselines)
    ctl.reset(make_track_info(stadium))
    speed, steering = ctl.step(0.0, 0.0, 0.0, 1.0, 0.0, np.full(72, np.inf))
    assert speed == pytest.approx(0.0)
    assert steering == pytest.approx(0.0)


def test_rejects_missing_baselines() -> None:
    with pytest.raises(ControllerError, match="no arguments"):
        load_controller(WALL_FOLLOW)


def test_missing_gain_key_is_rejected(config: Config) -> None:
    baselines = {k: dict(v) for k, v in config.baselines.items()}
    del baselines["wall_follow"]["kp"]
    with pytest.raises(ControllerError, match="missing key"):
        load_controller(WALL_FOLLOW, baselines=baselines)


def test_steers_toward_nearest_wall(config: Config, stadium: Track) -> None:
    ctl = load_controller(WALL_FOLLOW, baselines=config.baselines)
    ctl.reset(make_track_info(stadium))
    left_wall = np.full(72, np.inf)
    left_wall[3] = 40.0
    right_wall = np.full(72, np.inf)
    right_wall[69] = 40.0
    _, steer_left = ctl.step(0.0, 0.0, 0.0, 1.0, 0.0, left_wall)
    _, steer_right = ctl.step(0.0, 0.0, 0.0, 1.0, 0.0, right_wall)
    assert steer_left > 0.0
    assert steer_right < 0.0


def test_wall_follow_finishes_three_laps_clean(config: Config, stadium: Track) -> None:
    ctl = load_controller(WALL_FOLLOW, baselines=config.baselines)
    result = run_race(stadium, config, [ctl], ["wall_follow"], mode="time-trial")
    r = result.results[0]
    assert r.status is VehicleStatus.FINISHED
    assert r.laps_completed == 3
    assert r.crashes == 0
    assert r.best_lap is not None


def test_wall_follow_races_pure_pursuit(config: Config, stadium: Track) -> None:
    pp = load_controller(PURE_PURSUIT, baselines=config.baselines)
    wf = load_controller(WALL_FOLLOW, baselines=config.baselines)
    result = run_race(
        stadium, config, [pp, wf], ["pure_pursuit", "wall_follow"], mode="race"
    )
    by_name = {r.name: r for r in result.results}
    assert set(by_name) == {"pure_pursuit", "wall_follow"}
    pp_result = by_name["pure_pursuit"]
    wf_result = by_name["wall_follow"]
    assert pp_result.status is VehicleStatus.FINISHED
    assert pp_result.laps_completed == 3
    assert pp_result.finish_order == 1
    # The wall-follower is ~4x slower, so the fast car laps it; it either
    # survives or DNFs on max crashes. Either way the race ends with a valid
    # terminal status for every car.
    assert wf_result.status in (VehicleStatus.FINISHED, VehicleStatus.DNF)
