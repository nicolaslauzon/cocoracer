from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml


class ConfigError(ValueError):
    pass


def _require(mapping: dict, key: str, section: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"missing required key '{key}' in [{section}]")
    return mapping[key]


@dataclass
class SimConfig:
    tick_hz: float = 40.0
    physics_substeps: int = 4

    @property
    def tick_dt(self) -> float:
        return 1.0 / self.tick_hz


@dataclass
class VehicleConfig:
    lf: float = 0.15875
    lr: float = 0.17145
    length: float = 0.5
    width: float = 0.4
    max_speed: float = 10.0
    min_speed: float = 0.0
    max_accel: float = 3.0
    max_steer: float = 0.5
    min_steer: float = -0.5
    max_steer_rate: float = 3.0
    min_steer_rate: float = -3.0

    @property
    def wheelbase(self) -> float:
        return self.lf + self.lr


@dataclass
class SensorConfig:
    beam_count: int = 72

    @property
    def beam_angles(self) -> np.ndarray:
        return np.arange(self.beam_count) * (2.0 * np.pi / self.beam_count)


@dataclass
class RaceConfig:
    laps: int = 3
    time_limit: float = 300.0
    crash_pause: float = 0.5
    ghost_duration: float = 1.5
    collision_distance: float = 0.5
    max_crashes: int = 5
    countdown: float = 3.0
    grid_spacing: float = 1.5


@dataclass
class Segment:
    type: str
    length: float = 0.0
    radius: float = 0.0
    angle: float = 0.0


@dataclass
class TrackSpec:
    name: str
    width: float
    resolution: float
    segments: list[Segment] = field(default_factory=list)


@dataclass
class Config:
    sim: SimConfig
    vehicle: VehicleConfig
    sensor: SensorConfig
    race: RaceConfig
    tracks: dict[str, TrackSpec]
    baselines: dict[str, dict]
    default_track: str


def _build_track(name: str, data: dict) -> TrackSpec:
    section = f"tracks.{name}"
    raw_segments = _require(data, "segments", section)
    segments: list[Segment] = []
    for i, raw in enumerate(raw_segments):
        seg_section = f"{section}.segments[{i}]"
        seg_type = str(_require(raw, "type", seg_section))
        if seg_type == "straight":
            segments.append(
                Segment("straight", length=float(_require(raw, "length", seg_section)))
            )
        elif seg_type == "turn":
            segments.append(
                Segment(
                    "turn",
                    radius=float(_require(raw, "radius", seg_section)),
                    angle=float(_require(raw, "angle", seg_section)),
                )
            )
        else:
            raise ConfigError(f"unknown segment type '{seg_type}' in {seg_section}")
    return TrackSpec(
        name=name,
        width=float(_require(data, "width", section)),
        resolution=float(_require(data, "resolution", section)),
        segments=segments,
    )


def load_config(path: Path | str) -> Config:
    with open(path) as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(f"param file {path} must be a mapping")

    sim_raw = raw.get("simulation", {})
    sim = SimConfig(
        tick_hz=float(sim_raw.get("tick_hz", 40.0)),
        physics_substeps=int(sim_raw.get("physics_substeps", 4)),
    )

    vehicle = _vehicle_from(raw.get("vehicle", {}))
    sensor = SensorConfig(beam_count=int(raw.get("sensor", {}).get("beam_count", 72)))

    race_raw = raw.get("race", {})
    race = RaceConfig(
        laps=int(race_raw.get("laps", 3)),
        time_limit=float(race_raw.get("time_limit", 300.0)),
        crash_pause=float(race_raw.get("crash_pause", 0.5)),
        ghost_duration=float(race_raw.get("ghost_duration", 1.5)),
        collision_distance=float(race_raw.get("collision_distance", 0.5)),
        max_crashes=int(race_raw.get("max_crashes", 5)),
        countdown=float(race_raw.get("countdown", 3.0)),
        grid_spacing=float(race_raw.get("grid_spacing", 1.5)),
    )

    tracks_raw = _require(raw, "tracks", "root")
    tracks = {name: _build_track(name, data) for name, data in tracks_raw.items()}
    default_track = raw.get("default_track", next(iter(tracks)))
    if default_track not in tracks:
        raise ConfigError(f"default_track '{default_track}' not defined in tracks")

    baselines = raw.get("baselines", {}) or {}

    return Config(
        sim=sim,
        vehicle=vehicle,
        sensor=sensor,
        race=race,
        tracks=tracks,
        baselines=baselines,
        default_track=default_track,
    )


def _vehicle_from(data: dict) -> VehicleConfig:
    return VehicleConfig(
        lf=float(data.get("lf", 0.15875)),
        lr=float(data.get("lr", 0.17145)),
        length=float(data.get("length", 0.5)),
        width=float(data.get("width", 0.4)),
        max_speed=float(data.get("max_speed", 10.0)),
        min_speed=float(data.get("min_speed", 0.0)),
        max_accel=float(data.get("max_accel", 3.0)),
        max_steer=float(data.get("max_steer", 0.5)),
        min_steer=float(data.get("min_steer", -0.5)),
        max_steer_rate=float(data.get("max_steer_rate", 3.0)),
        min_steer_rate=float(data.get("min_steer_rate", -3.0)),
    )
