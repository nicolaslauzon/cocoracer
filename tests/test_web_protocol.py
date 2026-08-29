"""Tests for the web protocol serializers (pure state -> JSON)."""

import dataclasses
import json
import math

import numpy as np
import pytest

from cocoracer.config import Config
from cocoracer.controller import Controller, TrackInfo
from cocoracer.engine import (
    RaceEngine,
    RaceResult,
    RaceSnapshot,
    VehicleSnapshot,
    VehicleStatus,
    run_race,
)
from cocoracer.race_state import DnfReason
from cocoracer.track import Track
from cocoracer.web.protocol import build_dynamic_message, build_static_message


def test_static_message_shape(stadium: Track, config: Config) -> None:
    msg = json.loads(build_static_message(stadium, config))
    assert msg["type"] == "static"
    assert msg["track"] == stadium.name
    assert msg["track_length"] == pytest.approx(stadium.track_length)
    assert msg["vehicle"] == {
        "length": pytest.approx(config.vehicle.length),
        "width": pytest.approx(config.vehicle.width),
    }
    line = msg["centerline"]
    assert len(line) >= 4
    assert all(isinstance(p, list) and len(p) == 2 for p in line)
    assert line[0] == pytest.approx(
        [stadium.centerline[0, 0], stadium.centerline[0, 1]]
    )
    for key in ("left_wall", "right_wall"):
        wall = msg[key]
        assert len(wall) >= 3
        assert all(isinstance(p, list) and len(p) == 2 for p in wall)
    assert msg["start_line"] == {
        "left": pytest.approx([stadium.left_wall[0, 0], stadium.left_wall[0, 1]]),
        "right": pytest.approx([stadium.right_wall[0, 0], stadium.right_wall[0, 1]]),
    }
    assert "grid" not in msg
    assert "track_width" not in msg


def test_static_message_walls_downsampled_to_one_metre(
    stadium: Track, config: Config
) -> None:
    walls_before = (stadium.left_wall.copy(), stadium.right_wall.copy())
    msg = json.loads(build_static_message(stadium, config))
    for key, original in zip(("left_wall", "right_wall"), walls_before, strict=True):
        sent = np.asarray(msg[key])
        gaps = np.hypot(np.diff(sent[:, 0]), np.diff(sent[:, 1]))
        assert len(gaps) > 100
        assert np.allclose(gaps, 1.0, atol=0.01)
        # Closed curve: the payload repeats its first point at the end.
        assert sent[0] == pytest.approx(sent[-1])
        assert len(sent) < len(original)
    # The in-process track keeps its full-resolution curves.
    assert np.array_equal(stadium.left_wall, walls_before[0])
    assert np.array_equal(stadium.right_wall, walls_before[1])


def _vehicle(i: int, status: VehicleStatus) -> VehicleSnapshot:
    return VehicleSnapshot(
        name=f"v{i}",
        id=i,
        status=status,
        x=1.0 * i,
        y=2.0 * i,
        yaw=0.5,
        speed=1.0 * i,
        steering=0.1 * i,
        laps_completed=i,
        best_lap=10.0 + i if i > 0 else None,
        last_lap=11.0 + i if i > 0 else None,
        crashes=i,
        finish_time=20.0 + i if status is VehicleStatus.FINISHED else None,
        dnf_reason=DnfReason.TIMEOUT if status is VehicleStatus.DNF else None,
    )


def _snapshot(track: Track, statuses: list[VehicleStatus]) -> RaceSnapshot:
    return RaceSnapshot(
        time=1.25,
        track=track,
        vehicles=tuple(_vehicle(i, s) for i, s in enumerate(statuses)),
    )


def test_dynamic_message_shape(stadium: Track) -> None:
    scan = np.array([0.5, np.inf, 1.5])
    snap = _snapshot(stadium, [VehicleStatus.RACING])
    msg = json.loads(build_dynamic_message(snap, "racing", 0.0, [scan]))
    assert msg["type"] == "dynamic"
    assert msg["time"] == pytest.approx(1.25)
    assert msg["phase"] == "racing"
    assert msg["countdown"] == 0.0
    assert len(msg["vehicles"]) == 1
    v = msg["vehicles"][0]
    assert v["id"] == 0
    assert v["name"] == "v0"
    assert (v["x"], v["y"], v["yaw"]) == (0.0, 0.0, 0.5)
    assert v["speed"] == 0.0
    assert v["steering"] == 0.0
    assert v["laps"] == 0
    assert v["status"] == "racing"
    assert v["best_lap"] is None
    assert v["last_lap"] is None
    assert v["crashes"] == 0
    assert v["finish_time"] is None
    assert v["scan"] == [0.5, None, 1.5]


def test_dynamic_message_represents_all_statuses(stadium: Track) -> None:
    statuses = [
        VehicleStatus.RACING,
        VehicleStatus.PAUSED,
        VehicleStatus.GHOST,
        VehicleStatus.FINISHED,
        VehicleStatus.DNF,
    ]
    snap = _snapshot(stadium, statuses)
    msg = json.loads(build_dynamic_message(snap, "racing", 0.0, [None] * len(statuses)))
    assert [v["status"] for v in msg["vehicles"]] == [
        "racing",
        "paused",
        "ghost",
        "finished",
        "dnf",
    ]
    finished, dnf = msg["vehicles"][3], msg["vehicles"][4]
    assert finished["finish_time"] == pytest.approx(23.0)
    assert dnf["finish_time"] is None
    assert msg["vehicles"][1]["best_lap"] == pytest.approx(11.0)
    assert msg["vehicles"][0]["best_lap"] is None


def test_dynamic_message_null_for_no_hit_and_missing_scan(stadium: Track) -> None:
    scan = np.array([np.inf, 2.0, np.inf])
    snap = _snapshot(stadium, [VehicleStatus.RACING, VehicleStatus.PAUSED])
    msg = json.loads(build_dynamic_message(snap, "countdown", 2.5, [scan, None]))
    first, second = msg["vehicles"]
    assert first["scan"] == [None, 2.0, None]
    assert second["scan"] is None
    assert msg["phase"] == "countdown"
    assert msg["countdown"] == pytest.approx(2.5)


def test_dynamic_message_carries_waiting_phase(stadium: Track, config: Config) -> None:
    engine = RaceEngine(stadium, config, [Sitter()], ["sitter"], auto_start=False)
    msg = json.loads(
        build_dynamic_message(
            engine.snapshot(), engine.phase, engine.countdown, engine.last_scans
        )
    )
    assert msg["type"] == "dynamic"
    assert msg["phase"] == "waiting"
    assert msg["time"] == 0.0


class Sitter(Controller):
    """Sits on the grid: zero speed, zero steer."""

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


def test_serializers_are_pure(stadium: Track, config: Config) -> None:
    scan = np.array([0.5, np.inf])
    snap = _snapshot(stadium, [VehicleStatus.RACING, VehicleStatus.GHOST])
    static = build_static_message(stadium, config)
    dynamic = build_dynamic_message(snap, "racing", 0.0, [scan, None])
    occupied_before = stadium.occupied.copy()
    time_before = snap.time
    assert build_static_message(stadium, config) == static
    assert build_dynamic_message(snap, "racing", 0.0, [scan, None]) == dynamic
    assert bool((stadium.occupied == occupied_before).all())
    assert snap.time == time_before


class CenterlineDriver(Controller):
    """Follows the stadium centerline: zero steer on the straights, a
    steady steer through both 180-degree arcs."""

    ARC_STEER = math.atan(1.65 / 40.0)

    def __init__(self, speed: float) -> None:
        self._speed = speed
        self._s = 0.0
        self._length = 491.327

    def reset(self, track_info: TrackInfo) -> None:
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
        in_arc = (120.0 <= s < 120.0 + 40.0 * math.pi) or (
            240.0 + 40.0 * math.pi <= s < self._length
        )
        return self._speed, (self.ARC_STEER if in_arc else 0.0)


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


def test_live_tick_loop_matches_headless_run_race(
    stadium: Track, config: Config
) -> None:
    config = dataclasses.replace(config, race=dataclasses.replace(config.race, laps=1))
    headless = run_race(stadium, config, [CenterlineDriver(20.0)], ["runner"])
    engine = RaceEngine(stadium, config, [CenterlineDriver(20.0)], ["runner"])
    while not engine.finished:
        engine.tick()
    live = engine.results
    assert _fingerprint(headless) == _fingerprint(live)
    assert live.results[0].status is VehicleStatus.FINISHED
    assert engine.phase == "finished"
    assert engine.countdown == 0.0
