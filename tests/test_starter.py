"""Tests for the onboarding starter controller (issue 17)."""

from pathlib import Path

import numpy as np
import pytest

from cocoracer.config import Config
from cocoracer.controller import load_controller, make_track_info
from cocoracer.engine import run_race
from cocoracer.race_state import VehicleStatus
from cocoracer.track import Track

REPO_ROOT = Path(__file__).resolve().parent.parent
STARTER = REPO_ROOT / "controllers" / "starter.py"
PURE_PURSUIT = REPO_ROOT / "controllers" / "pure_pursuit.py"


def test_starter_loads_without_baselines(config: Config, stadium: Track) -> None:
    ctl = load_controller(STARTER)
    ctl.reset(make_track_info(stadium))
    speed, steering = ctl.step(0.0, 0.0, 0.0, 1.0, 0.0, np.full(72, np.inf))
    # No walls anywhere: cruise at full speed, no turn.
    assert speed == pytest.approx(3.0)
    assert steering == pytest.approx(0.0)


def test_starter_finishes_three_laps_clean(config: Config, stadium: Track) -> None:
    ctl = load_controller(STARTER)
    result = run_race(stadium, config, [ctl], ["starter"], mode="time-trial")
    r = result.results[0]
    assert r.status is VehicleStatus.FINISHED
    assert r.laps_completed == 3
    assert r.crashes == 0
    assert r.best_lap is not None


def test_starter_races_pure_pursuit(config: Config, stadium: Track) -> None:
    pp = load_controller(PURE_PURSUIT, baselines=config.baselines)
    starter = load_controller(STARTER)
    result = run_race(
        stadium, config, [pp, starter], ["pure_pursuit", "starter"], mode="race"
    )
    by_name = {r.name: r for r in result.results}
    assert set(by_name) == {"pure_pursuit", "starter"}
    # The pace setter wins; the slow starter either keeps up or DNFs on
    # rear-ends. Either way the race ends with a valid terminal status.
    assert by_name["pure_pursuit"].finish_order == 1
    assert by_name["starter"].status in (VehicleStatus.FINISHED, VehicleStatus.DNF)
