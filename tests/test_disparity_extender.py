"""Tests for the disparity-extender reactive baseline (issue 15).

Disparity extender is the reactive, laser-only companion to pure pursuit:
no centerline, just the full-circle scan. It extends each range edge across
the car's width, aims the P/D law at the farthest beam of the extended front
sector, and caps speed by target distance and the friction limit for the
commanded steering angle.
"""

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
DISPARITY_EXTENDER = REPO_ROOT / "controllers" / "disparity_extender.py"
PURE_PURSUIT = REPO_ROOT / "controllers" / "pure_pursuit.py"


def test_loader_injects_baselines(config: Config, stadium: Track) -> None:
    ctl = load_controller(DISPARITY_EXTENDER, baselines=config.baselines)
    ctl.reset(make_track_info(stadium))
    # An empty (all-inf) scan has no target, so the car holds minimum speed
    # straight ahead.
    speed, steering = ctl.step(0.0, 0.0, 0.0, 1.0, 0.0, np.full(72, np.inf))
    assert speed == pytest.approx(
        float(config.baselines["disparity_extender"]["min_speed"])
    )
    assert steering == pytest.approx(0.0)


def test_rejects_missing_baselines() -> None:
    with pytest.raises(ControllerError, match="no arguments"):
        load_controller(DISPARITY_EXTENDER)


def test_missing_parameter_key_is_rejected(config: Config) -> None:
    broken = {
        "disparity_extender": {
            key: value
            for key, value in config.baselines["disparity_extender"].items()
            if key != "kp"
        }
    }
    with pytest.raises(ControllerError, match="missing key"):
        load_controller(DISPARITY_EXTENDER, baselines=broken)


def test_disparity_extender_finishes_three_laps_clean(
    config: Config, stadium: Track
) -> None:
    ctl = load_controller(DISPARITY_EXTENDER, baselines=config.baselines)
    result = run_race(stadium, config, [ctl], ["disparity_extender"], mode="time-trial")
    r = result.results[0]
    assert r.status is VehicleStatus.FINISHED
    assert r.laps_completed == 3
    assert r.crashes == 0
    assert r.best_lap is not None


def test_disparity_extender_races_pure_pursuit(config: Config, stadium: Track) -> None:
    de = load_controller(DISPARITY_EXTENDER, baselines=config.baselines)
    pp = load_controller(PURE_PURSUIT, baselines=config.baselines)
    result = run_race(
        stadium,
        config,
        [pp, de],
        ["pure_pursuit", "disparity_extender"],
        mode="race",
    )
    by_name = {r.name: r for r in result.results}
    assert set(by_name) == {"pure_pursuit", "disparity_extender"}
    pp_result = by_name["pure_pursuit"]
    de_result = by_name["disparity_extender"]
    # The reactive baseline is drivable in a shared race: it completes all
    # three laps (it may be clipped while being lapped) and pure pursuit,
    # the faster car, wins.
    assert de_result.status is VehicleStatus.FINISHED
    assert de_result.laps_completed == 3
    assert de_result.best_lap is not None
    assert pp_result.status is VehicleStatus.FINISHED
    assert pp_result.laps_completed == 3
    assert pp_result.finish_order == 1
    assert de_result.finish_order == 2
