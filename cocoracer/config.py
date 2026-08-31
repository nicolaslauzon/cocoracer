import json
from dataclasses import dataclass
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
    lf: float = 0.79
    lr: float = 0.86
    length: float = 2.5
    width: float = 2.0
    max_speed: float = 25.0
    min_speed: float = 0.0
    max_accel: float = 8.0
    max_steer: float = 0.5
    min_steer: float = -0.5
    max_steer_rate: float = 4.0
    min_steer_rate: float = -4.0

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
    time_limit: float = 600.0
    crash_pause: float = 2.0
    ghost_duration: float = 1.5
    collision_distance: float = 2.5
    max_crashes: int = 5
    countdown: float = 3.0


@dataclass
class Segment:
    type: str
    length: float = 0.0
    radius: float = 0.0
    angle: float = 0.0


@dataclass
class MapSpec:
    image: Path
    scale: float
    threshold: int
    direction: str
    start: tuple[int, int]


@dataclass
class TrackSpec:
    name: str
    width: float
    resolution: float
    segments: list[Segment] | None = None
    centerline: list[tuple[float, float]] | None = None
    map: MapSpec | None = None


@dataclass
class Config:
    sim: SimConfig
    vehicle: VehicleConfig
    sensor: SensorConfig
    race: RaceConfig
    tracks: dict[str, TrackSpec]
    baselines: dict[str, dict]
    default_track: str


def _load_track_file(ref: Any, base_dir: Path, section: str) -> dict:
    if not isinstance(ref, str):
        raise ConfigError(f"'file' in {section} must be a string path")
    path = base_dir / ref
    if not path.is_file():
        raise ConfigError(f"track file '{ref}' for {section} not found")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"track file '{ref}' for {section} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ConfigError(
            f"track file '{ref}' for {section} must contain a JSON object"
        )
    return data


def _segments_from(data: dict, section: str) -> list[Segment] | None:
    if "segments" not in data:
        return None
    raw_segments = data["segments"]
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
    return segments


def _centerline_from(data: dict, section: str) -> list[tuple[float, float]] | None:
    if "centerline" not in data:
        return None
    raw = data["centerline"]
    if not isinstance(raw, list) or len(raw) < 4:
        raise ConfigError(
            f"track '{section}' centerline must list at least 4 [x, y] points"
        )
    points: list[tuple[float, float]] = []
    for i, point in enumerate(raw):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ConfigError(f"track '{section}' centerline[{i}] must be [x, y]")
        points.append((float(point[0]), float(point[1])))
    return points


def _build_track(name: str, data: dict, base_dir: Path) -> TrackSpec:
    section = f"tracks.{name}"
    track_data = (
        _load_track_file(data["file"], base_dir, section) if "file" in data else data
    )
    segments = _segments_from(track_data, section)
    centerline = _centerline_from(track_data, section)
    if segments is None and centerline is None:
        raise ConfigError(f"track '{section}' needs 'segments' or 'centerline'")
    if segments is not None and centerline is not None:
        raise ConfigError(
            f"track '{section}' declares both 'segments' and 'centerline'"
        )
    return TrackSpec(
        name=name,
        width=float(_require(track_data, "width", section)),
        resolution=float(_require(track_data, "resolution", section)),
        segments=segments,
        centerline=centerline,
    )


def _map_image_from(data: dict, section: str, base_dir: Path) -> Path:
    ref = _require(data, "map", section)
    if not isinstance(ref, str):
        raise ConfigError(f"'map' in {section} must be a string path")
    path = base_dir / ref
    if not path.is_file():
        raise ConfigError(f"map image '{ref}' for {section} not found")
    return path


def _map_start_from(data: dict, section: str) -> tuple[int, int]:
    raw = _require(data, "start", section)
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ConfigError(f"map track '{section}' start must be [col, row]")
    try:
        col, row = int(raw[0]), int(raw[1])
    except (TypeError, ValueError):
        raise ConfigError(
            f"map track '{section}' start must be two integer pixels"
        ) from None
    return (col, row)


def _map_spec_from(
    name: str,
    data: dict,
    base_dir: Path,
    default_scale: float,
    default_threshold: int,
) -> MapSpec:
    from cocoracer.maptrack import MAP_DIRECTIONS

    section = f"maps.tracks.{name}"
    if not isinstance(data, dict):
        raise ConfigError(f"map track '{section}' must be a mapping")
    direction = str(_require(data, "direction", section))
    if direction not in MAP_DIRECTIONS:
        raise ConfigError(f"map track '{section}' direction must be 'cw' or 'ccw'")
    return MapSpec(
        image=_map_image_from(data, section, base_dir),
        scale=float(data.get("scale", default_scale)),
        threshold=int(data.get("threshold", default_threshold)),
        direction=direction,
        start=_map_start_from(data, section),
    )


def _maps_from(raw_maps: dict | None, base_dir: Path) -> dict[str, MapSpec]:
    # Imported lazily: maptrack imports track, which imports config.
    from cocoracer.maptrack import DEFAULT_SCALE
    from cocoracer.pgm import DEFAULT_THRESHOLD

    if raw_maps is None:
        return {}
    if not isinstance(raw_maps, dict):
        raise ConfigError("'maps' must be a mapping")
    raw_tracks = raw_maps.get("tracks", {})
    if not isinstance(raw_tracks, dict):
        raise ConfigError("'tracks' in maps must be a mapping")
    default_scale = float(raw_maps.get("scale", DEFAULT_SCALE))
    default_threshold = int(raw_maps.get("threshold", DEFAULT_THRESHOLD))
    return {
        name: _map_spec_from(name, data, base_dir, default_scale, default_threshold)
        for name, data in raw_tracks.items()
    }


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
        time_limit=float(race_raw.get("time_limit", 600.0)),
        crash_pause=float(race_raw.get("crash_pause", 2.0)),
        ghost_duration=float(race_raw.get("ghost_duration", 1.5)),
        collision_distance=float(race_raw.get("collision_distance", 2.5)),
        max_crashes=int(race_raw.get("max_crashes", 5)),
        countdown=float(race_raw.get("countdown", 3.0)),
    )

    tracks_raw = _require(raw, "tracks", "root")
    base_dir = Path(path).resolve().parent
    tracks = {
        name: _build_track(name, data, base_dir) for name, data in tracks_raw.items()
    }
    maps = _maps_from(raw.get("maps"), base_dir)
    for name, spec in maps.items():
        if name in tracks:
            raise ConfigError(f"track '{name}' is declared in both 'tracks' and 'maps'")
        tracks[name] = TrackSpec(name=name, width=0.0, resolution=0.0, map=spec)
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
        lf=float(data.get("lf", 0.79)),
        lr=float(data.get("lr", 0.86)),
        length=float(data.get("length", 2.5)),
        width=float(data.get("width", 2.0)),
        max_speed=float(data.get("max_speed", 25.0)),
        min_speed=float(data.get("min_speed", 0.0)),
        max_accel=float(data.get("max_accel", 8.0)),
        max_steer=float(data.get("max_steer", 0.5)),
        min_steer=float(data.get("min_steer", -0.5)),
        max_steer_rate=float(data.get("max_steer_rate", 4.0)),
        min_steer_rate=float(data.get("min_steer_rate", -4.0)),
    )
