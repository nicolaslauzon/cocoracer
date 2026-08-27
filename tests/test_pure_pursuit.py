"""Tests for the pure-pursuit reference controller (issue 09)."""

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
PURE_PURSUIT = REPO_ROOT / "controllers" / "pure_pursuit.py"
STUB = REPO_ROOT / "controllers" / "open_loop.py"


def test_track_info_carries_centerline(stadium: Track) -> None:
    info = make_track_info(stadium)
    assert len(info.centerline) == len(stadium.centerline)
    assert all(len(point) == 2 for point in info.centerline)


def test_loader_injects_baselines(config: Config, stadium: Track) -> None:
    ctl = load_controller(PURE_PURSUIT, baselines=config.baselines)
    ctl.reset(make_track_info(stadium))
    speed, _ = ctl.step(0.0, 0.0, 0.0, 1.0, 0.0, np.full(72, np.inf))
    assert speed == pytest.approx(
        float(config.baselines["pure_pursuit"]["target_speed"])
    )


def test_baselines_controller_rejects_missing_baselines() -> None:
    with pytest.raises(ControllerError, match="no arguments"):
        load_controller(PURE_PURSUIT)


def test_pure_pursuit_finishes_three_laps_clean(config: Config, stadium: Track) -> None:
    ctl = load_controller(PURE_PURSUIT, baselines=config.baselines)
    result = run_race(stadium, config, [ctl], ["pure_pursuit"], mode="time-trial")
    r = result.results[0]
    assert r.status is VehicleStatus.FINISHED
    assert r.laps_completed == 3
    assert r.crashes == 0
    assert r.best_lap is not None


def test_pure_pursuit_beats_open_loop_stub(config: Config, stadium: Track) -> None:
    pp = load_controller(PURE_PURSUIT, baselines=config.baselines)
    stub = load_controller(STUB, baselines=config.baselines)
    result = run_race(
        stadium, config, [pp, stub], ["pure_pursuit", "open_loop"], mode="race"
    )
    by_name = {r.name: r for r in result.results}
    pp_result = by_name["pure_pursuit"]
    stub_result = by_name["open_loop"]
    assert pp_result.status is VehicleStatus.FINISHED
    assert pp_result.laps_completed == 3
    assert pp_result.finish_order == 1
    assert stub_result.status is VehicleStatus.DNF
    assert stub_result.laps_completed == 0
