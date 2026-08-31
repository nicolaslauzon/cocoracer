import argparse
import sys
from pathlib import Path

from cocoracer.cli import _load_single, _print_results, _report, _run_live
from cocoracer.config import load_config
from cocoracer.track import build_track

BUNDLED_DIR = Path(__file__).resolve().parent / "bundled"
PARAMS_FILE = BUNDLED_DIR / "default.yaml"
TRACK = "stadium"
OPPONENT = "wall_follow.py"


def _resolve_controller(name: str) -> Path:
    path = Path(name)
    if path.is_file():
        return path
    raise SystemExit(f"controller not found: {name}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="demo",
        description="Racing demo: program your controller and race on the stadium.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    tt = sub.add_parser("time-trial", help="race one controller alone")
    tt.add_argument("controller", help="controller file (e.g. stub.py)")
    race = sub.add_parser("race", help="race your controller against the wall follower")
    race.add_argument("controller", help="your controller file (e.g. stub.py)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = load_config(PARAMS_FILE)
    config.race.laps = 3
    track = build_track(config.tracks[TRACK])
    my_path = _resolve_controller(args.controller)
    _report(config, TRACK, track, [my_path], args.command)

    if args.command == "time-trial":
        instance = _load_single(my_path, config.baselines)
        result = _run_live(config, track, [instance], None, "time-trial", port=8000)
    else:
        opponent_path = BUNDLED_DIR / OPPONENT
        if not opponent_path.is_file():
            raise SystemExit(f"bundled opponent not found: {opponent_path}")
        my_instance = _load_single(my_path, config.baselines)
        opponent_instance = _load_single(opponent_path, config.baselines)
        result = _run_live(
            config,
            track,
            [my_instance, opponent_instance],
            [my_path.stem, "wall_follow"],
            "race",
            port=8000,
        )
    _print_results(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
