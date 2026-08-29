"""Perf test: an 8-vehicle stadium race finishes with the per-tick cost
inside the real-time budget (one tick period)."""

import time
from pathlib import Path

import numpy as np
import pytest

from cocoracer.config import Config
from cocoracer.controller import load_controller
from cocoracer.engine import RaceEngine, VehicleStatus
from cocoracer.track import Track

REPO_ROOT = Path(__file__).resolve().parent.parent
PURE_PURSUIT = REPO_ROOT / "controllers" / "pure_pursuit.py"


@pytest.mark.slow
def test_eight_vehicle_tick_cost_stays_within_budget(
    stadium: Track, config: Config
) -> None:
    controllers = [
        load_controller(PURE_PURSUIT, baselines=config.baselines) for _ in range(8)
    ]
    engine = RaceEngine(
        stadium, config, controllers, [f"v{i}" for i in range(8)], mode="race"
    )
    countdown = int(round(config.race.countdown / config.sim.tick_dt))
    for _ in range(countdown):
        engine.tick()
    samples: list[float] = []
    while not engine.finished:
        start = time.perf_counter()
        engine.tick()
        samples.append((time.perf_counter() - start) * 1000.0)
    assert len(samples) > 100
    # Drop the first ticks (JAX dispatch and allocation warmup); the mean
    # over the steady state must beat the real-time budget. The max tick
    # is deliberately not asserted on: single-tick variance on CI.
    measured = np.array(samples[50:])
    assert measured.mean() <= config.sim.tick_dt * 1000.0
    results = engine.results.results
    assert len(results) == 8
    assert all(r.status is VehicleStatus.FINISHED for r in results)
