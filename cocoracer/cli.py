import argparse
import queue
import sys
import time
from pathlib import Path

from cocoracer.config import Config, load_config
from cocoracer.controller import Controller, ControllerError, load_controller
from cocoracer.engine import RaceEngine, RaceResult, run_race
from cocoracer.track import Track, build_track

PARAMS_DIR = Path(__file__).resolve().parent.parent / "params"


def _default_params() -> Path:
    return PARAMS_DIR / "default.yaml"


def _add_race_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--track",
        default=None,
        help="track name from the param file (default: the configured default track)",
    )
    parser.add_argument(
        "--controller",
        required=True,
        metavar="PATH[,PATH...]",
        help="comma-separated controller file paths to load, e.g. "
        "controllers/starter.py,controllers/pure_pursuit.py",
    )
    parser.add_argument(
        "--laps",
        type=int,
        default=None,
        help="override the lap count from the param file",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="run headless: skip the live web view and just print the results",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port for the live web view, ignored with --no-web (default 8000)",
    )


def build_parser() -> argparse.ArgumentParser:
    examples = (
        "examples:\n"
        "  # time the starter controller alone (headless)\n"
        "  cocoracer time-trial --controller controllers/starter.py --no-web\n"
        "\n"
        "  # race the starter against two baselines, with the live web view\n"
        "  cocoracer race \\\n"
        "    --controller controllers/starter.py,controllers/pure_pursuit.py,controllers/wall_follow.py\n"
        "\n"
        "  # three-vehicle race on the Spa circuit for five laps\n"
        "  cocoracer race --track spa --laps 5 \\\n"
        "    --controller controllers/starter.py,controllers/wall_follow.py,controllers/disparity_extender.py\n"
    )
    parser = argparse.ArgumentParser(
        prog="cocoracer",
        description=(
            "Program an autonomous racing controller and race it in a "
            "deterministic 2-D car."
        ),
        epilog=examples,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--params",
        type=Path,
        default=None,
        help="path to the YAML param file (default: params/default.yaml); "
        "must come before the subcommand",
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
        title="commands",
        description="time-trial races one controller alone; race pits two or more "
        "against each other head-to-head.",
    )
    time_trial = sub.add_parser(
        "time-trial",
        help="race a single controller alone on the track",
        description="Race a single controller alone on the track and print its "
        "lap times.",
    )
    _add_race_args(time_trial)
    race = sub.add_parser(
        "race",
        help="race two or more controllers head-to-head",
        description="Race two or more controllers head-to-head and print the "
        "classified results.",
    )
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
    print(f"track width:  {track.width:.3f} m")
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


def _load_single(path: Path, baselines: dict[str, dict] | None = None) -> Controller:
    try:
        return load_controller(path, baselines=baselines)
    except ControllerError as exc:
        raise SystemExit(str(exc)) from exc


def _names_for(paths: list[Path]) -> list[str]:
    stems = [path.stem for path in paths]
    counts = {stem: stems.count(stem) for stem in set(stems)}
    seen: dict[str, int] = {}
    names: list[str] = []
    for stem in stems:
        if counts[stem] > 1:
            seen[stem] = seen.get(stem, 0) + 1
            names.append(f"{stem} ({seen[stem]})")
        else:
            names.append(stem)
    return names


def _print_results(result: RaceResult) -> None:
    print()
    print(f"results ({result.track_name}):")
    for r in result.results:
        order = f"P{r.finish_order}" if r.finish_order is not None else "-"
        total = f"{r.total_time:.3f} s" if r.total_time is not None else "-"
        best = f"{r.best_lap:.3f} s" if r.best_lap is not None else "-"
        reason = f"  [{r.dnf_reason.value}]" if r.dnf_reason else ""
        print(
            f"  {order:<4} {r.name:<20} {r.status.value.upper():<10} "
            f"{r.laps_completed:>3} laps  {total:>10}  best {best:>10}  "
            f"crashes: {r.crashes}{reason}"
        )
    print(f"race time: {result.time:.3f} s")


def _drain_starts(start_queue: queue.Queue[None], engine: RaceEngine) -> None:
    """Release the waiting field if a client start message is queued.

    The first message wins: pop one, release, discard the rest.
    """
    try:
        start_queue.get_nowait()
    except queue.Empty:
        return
    engine.start()
    while True:
        try:
            start_queue.get_nowait()
        except queue.Empty:
            return


def _run_live(
    config: Config,
    track: Track,
    instances: list[Controller],
    names: list[str] | None,
    mode: str,
    port: int,
) -> RaceResult:
    from cocoracer.web.server import WebServer

    engine = RaceEngine(track, config, instances, names, mode=mode, auto_start=False)
    start_queue: queue.Queue[None] = queue.Queue()
    server = WebServer(engine, start_queue=start_queue, port=port)
    server.start()
    print(f"web view: {server.url}")
    try:
        next_tick = time.monotonic()
        period = config.sim.tick_dt
        while not engine.finished:
            _drain_starts(start_queue, engine)
            engine.tick()
            next_tick += period
            delay = next_tick - time.monotonic()
            if delay > 0:
                time.sleep(delay)
    finally:
        server.stop()
    return engine.results


def _run(
    config: Config,
    track: Track,
    instances: list[Controller],
    names: list[str] | None,
    mode: str,
    args: argparse.Namespace,
) -> int:
    if args.no_web:
        result = run_race(track, config, instances, names, mode=mode)
    else:
        result = _run_live(config, track, instances, names, mode, args.port)
    _print_results(result)
    return 0


def _run_time_trial(
    config: Config, track: Track, controllers: list[Path], args: argparse.Namespace
) -> int:
    if len(controllers) != 1:
        raise SystemExit("time-trial takes exactly one controller")
    return _run(
        config,
        track,
        [_load_single(controllers[0], config.baselines)],
        None,
        "time-trial",
        args,
    )


def _run_race(
    config: Config, track: Track, controllers: list[Path], args: argparse.Namespace
) -> int:
    if len(controllers) < 2:
        raise SystemExit("race takes two or more controllers")
    instances = [_load_single(path, config.baselines) for path in controllers]
    return _run(config, track, instances, _names_for(controllers), "race", args)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config, track_name, track, controllers = _resolve(args)
    _report(config, track_name, track, controllers, args.command)
    if args.command == "time-trial":
        return _run_time_trial(config, track, controllers, args)
    return _run_race(config, track, controllers, args)


if __name__ == "__main__":
    sys.exit(main())
