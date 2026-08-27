"""Player controller contract and file loader."""

import importlib.util
import inspect
import itertools
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cocoracer.track import Track


class ControllerError(ValueError):
    pass


@dataclass(frozen=True)
class TrackInfo:
    """Facts about the track handed to a controller at reset."""

    name: str
    track_length: float
    width: float
    start_x: float
    start_y: float
    start_yaw: float
    centerline: tuple[tuple[float, float], ...] = ()


def make_track_info(track: Track) -> TrackInfo:
    x, y, yaw = track.start_pose
    centerline = tuple((float(px), float(py)) for px, py in track.centerline[:, :2])
    return TrackInfo(
        name=track.name,
        track_length=track.track_length,
        width=track.half_width * 2.0,
        start_x=x,
        start_y=y,
        start_yaw=yaw,
        centerline=centerline,
    )


class Controller:
    """Base class for player controllers.

    Subclass it in a single file and implement `step`. The engine calls
    `reset` once before the first tick, then `step` once per tick (40 Hz)
    while the vehicle is racing or ghosting. One instance serves one
    vehicle, so instance state persists between ticks.

    `step` also receives `laser_scan`, the full-circle scan: a numpy
    array of beam distances in meters, one per beam. Beam 0 points
    straight ahead (the vehicle heading); beam i is at heading +
    i * 360 / len(laser_scan) degrees, increasing counter-clockwise. A
    beam stops at the first obstacle — a wall, or another racing
    vehicle (its collision circle; the scanning vehicle is never a
    target) — and reads ``np.inf`` if it hits nothing. There is no max
    range.
    """

    def reset(self, track_info: TrackInfo) -> None:
        """Called once before the first tick, to initialize internal state."""

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        """Return (target_speed, target_steering_angle) for this tick."""
        raise NotImplementedError


_MODULE_COUNTER = itertools.count()


def load_controller(
    path: Path | str, baselines: dict[str, dict] | None = None
) -> Controller:
    """Import a player file and return an instance of its controller class.

    The file must define exactly one concrete subclass of Controller. A
    class whose own ``__init__`` declares a ``baselines`` parameter is
    instantiated with ``cls(baselines=baselines)`` when a baselines
    mapping is passed in, and with no arguments otherwise; every other
    class is instantiated with no arguments.
    """
    file = Path(path)
    if not file.is_file():
        raise ControllerError(f"controller file not found: {file}")
    module_name = f"cocoracer_controller_{file.stem}_{next(_MODULE_COUNTER)}"
    spec = importlib.util.spec_from_file_location(module_name, file)
    if spec is None or spec.loader is None:
        raise ControllerError(f"cannot import controller file: {file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except ControllerError:
        raise
    except Exception as exc:
        raise ControllerError(f"error importing controller file {file}: {exc}") from exc
    classes = [
        obj
        for obj in vars(module).values()
        if isinstance(obj, type)
        and issubclass(obj, Controller)
        and obj is not Controller
        and obj.__module__ == module_name
    ]
    if len(classes) != 1:
        found = ", ".join(c.__name__ for c in classes) or "none"
        raise ControllerError(
            f"controller file {file} must define exactly one concrete Controller "
            f"subclass (found: {found})"
        )
    cls: type[Controller] = classes[0]
    if cls.step is Controller.step:
        raise ControllerError(
            f"controller class {cls.__name__} is not concrete (it does not "
            f"override step)"
        )
    positional = [
        name
        for name, p in inspect.signature(cls.step).parameters.items()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional) < 7:
        raise ControllerError(
            f"controller class {cls.__name__} step() must take "
            f"(x, y, yaw, speed, steering_angle, laser_scan)"
        )
    accepts_baselines = "baselines" in inspect.signature(cls.__init__).parameters
    try:
        if accepts_baselines and baselines is not None:
            return cls(baselines=baselines)  # type: ignore[call-arg]
        return cls()
    except TypeError as exc:
        raise ControllerError(
            f"controller class {cls.__name__} must be instantiable with no "
            f"arguments: {exc}"
        ) from exc
