import argparse
import sys
from pathlib import Path

from cocoracer.config import Config, load_config
from cocoracer.track import Track, build_track

PARAMS_DIR = Path(__file__).resolve().parent.parent / "params"


def _default_params() -> Path:
    return PARAMS_DIR / "default.yaml"


def _add_race_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--track", default=None, help="track name from the param file")
    parser.add_argument(
        "--controller",
        required=True,
        help="comma-separated controller file paths",
    )
    parser.add_argument("--laps", type=int, default=None, help="override lap count")
    parser.add_argument(
        "--no-web", action="store_true", help="disable the live web view"
    )
    parser.add_argument("--port", type=int, default=8000, help="web view port")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cocoracer", description="Program an autonomous controller and race it."
    )
    parser.add_argument(
        "--params", type=Path, default=None, help="path to the YAML param file"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    time_trial = sub.add_parser(
        "time-trial", help="race a single controller alone on the track"
    )
    _add_race_args(time_trial)
    race = sub.add_parser("race", help="race two or more controllers head-to-head")
    _add_race_args(race)
    return parser


def _resolve(args: argparse.Namespace) -> tuple[Config, str, Track, list[Path]]:
    params_path = args.params or _default_params()
    config = load_config(params_path)
    track_name = args.track or config.default_track
    if track_name not in config.tracks:
        raise SystemExit(
            f"unknown track '{track_name}' (available: {', '.join(config.tracks)})"
        )
    if args.laps is not None:
        config.race.laps = args.laps
    track = build_track(config.tracks[track_name])
    controllers = [
        Path(part.strip()) for part in args.controller.split(",") if part.strip()
    ]
    return config, track_name, track, controllers


def _report(
    config: Config, track_name: str, track: Track, controllers: list[Path], command: str
) -> None:
    print(f"command:     {command}")
    print(f"track:       {track_name}")
    print(f"track length: {track.track_length:.3f} m")
    print(f"track width:  {track.half_width * 2:.3f} m")
    print(
        f"grid:         {track.grid_shape[1]} x {track.grid_shape[0]} @ {track.resolution:.3f} m"
    )
    print(f"laps:         {config.race.laps}")
    print(
        f"tick:         {config.sim.tick_hz:.0f} Hz ({config.sim.physics_substeps} physics substeps)"
    )
    print(
        f"vehicle:      v_max={config.vehicle.max_speed} m/s, a_max={config.vehicle.max_accel} m/s^2, steer_max={config.vehicle.max_steer} rad"
    )
    print(f"sensor:       {config.sensor.beam_count} beams")
    print(f"controllers:  {len(controllers)}")
    for path in controllers:
        print(f"  - {path}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config, track_name, track, controllers = _resolve(args)
    _report(config, track_name, track, controllers, args.command)
    return 0


if __name__ == "__main__":
    sys.exit(main())
