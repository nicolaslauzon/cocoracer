"""Deterministic headless race engine.

One single-threaded fixed-step loop (40 Hz). In race mode the field
starts on a hardcoded zigzag grid behind the start/finish line and
holds while the countdown runs; when the countdown ends the lap trackers
re-anchor at the grid poses, so the first lap is timed from the
release. Per tick, in order: the controllers that may be stepped
(racing and ghost) are each handed a fresh full-circle laser scan —
walls plus the collision circles of racing vehicles, first hit wins
per beam — and stepped, the non-terminal vehicles are integrated by
the batched JAX dynamics, crash timers advance, crashes are detected
in one pass (racing vehicles whose footprint touches a wall, then
racing pairs closer than the collision distance — each vehicle at
most once, ghosts and paused vehicles can neither hit nor be hit)
and the crashed vehicles are reset to the nearest centerline pose
with the pause or DNF registered, laps are booked behind the
start/finish line plus mid-track checkpoint, and the race timeout is
checked. An engine built with auto_start=False sits in the waiting
phase with the clock frozen until start() releases the field.
"""

from dataclasses import dataclass

import numpy as np

from cocoracer.collision import collide
from cocoracer.config import Config
from cocoracer.controller import Controller, make_track_info
from cocoracer.dynamics import Dynamics, DynamicsParams
from cocoracer.lap_tracker import LapTracker
from cocoracer.race_state import DnfReason, RaceState, VehicleStatus
from cocoracer.sensor import fleet_scan
from cocoracer.track import Track
from cocoracer.vehicle import Vehicle

_TERMINAL = (VehicleStatus.FINISHED, VehicleStatus.DNF)
_MODES = ("time-trial", "race")
_GRID_ROW = 3.75
_GRID_OFFSET = 2.5


@dataclass
class VehicleResult:
    """Outcome for one vehicle, in the final race result."""

    name: str
    status: VehicleStatus
    finish_order: int | None
    total_time: float | None
    best_lap: float | None
    last_lap: float | None
    laps_completed: int
    crashes: int
    dnf_reason: DnfReason | None


@dataclass
class RaceResult:
    """Outcome of a finished race, DNFs ranked after finishers."""

    track_name: str
    time: float
    results: list[VehicleResult]


@dataclass(frozen=True)
class VehicleSnapshot:
    """Read-only per-vehicle state at one moment of the race."""

    name: str
    id: int
    status: VehicleStatus
    x: float
    y: float
    yaw: float
    speed: float
    steering: float
    laps_completed: int
    best_lap: float | None
    last_lap: float | None
    crashes: int
    finish_time: float | None
    dnf_reason: DnfReason | None
    last_crash: tuple[float, float] | None = None


@dataclass(frozen=True)
class RaceSnapshot:
    """Read-only state of the whole race at one moment."""

    time: float
    track: Track
    vehicles: tuple[VehicleSnapshot, ...]


class RaceEngine:
    """Fixed-step deterministic race simulation for one track."""

    def __init__(
        self,
        track: Track,
        config: Config,
        controllers: list[Controller],
        names: list[str] | None = None,
        mode: str = "time-trial",
        auto_start: bool = True,
    ) -> None:
        if mode not in _MODES:
            raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")
        if not controllers:
            raise ValueError("at least one controller is required")
        if names is None:
            names = [f"vehicle{i + 1}" for i in range(len(controllers))]
        if len(names) != len(controllers):
            raise ValueError("names and controllers must have the same length")
        self.track = track
        self.config = config
        self.time = 0.0
        self._last_scans: list[np.ndarray | None] = [None] * len(controllers)
        self._dt = config.sim.tick_dt
        self._laps = config.race.laps
        self._time_limit = config.race.time_limit
        self._pause_ticks = int(round(config.race.crash_pause / self._dt))
        self._ghost_ticks = int(round(config.race.ghost_duration / self._dt))
        self._max_crashes = config.race.max_crashes
        self._beam_angles = config.sensor.beam_angles
        self._collision_distance = config.race.collision_distance
        self._countdown_left = (
            int(round(config.race.countdown / self._dt)) if mode == "race" else 0
        )
        self._waiting = not auto_start
        poses = [
            self._grid_pose(i) if mode == "race" else track.start_pose
            for i in range(len(controllers))
        ]
        self.vehicles = [
            Vehicle(
                name=name,
                controller=ctl,
                x=x,
                y=y,
                yaw=yaw,
                state=RaceState(
                    pause_ticks=self._pause_ticks,
                    ghost_ticks=self._ghost_ticks,
                    max_crashes=self._max_crashes,
                    laps_target=self._laps,
                ),
                tracker=LapTracker(track.track_length, track.checkpoint_s),
            )
            for name, ctl, (x, y, yaw) in zip(names, controllers, poses, strict=True)
        ]
        self._length = config.vehicle.length
        self._width = config.vehicle.width
        self._dynamics = Dynamics(
            DynamicsParams.from_config(
                config.vehicle, config.sim.tick_dt, config.sim.physics_substeps
            ),
            config.sim.physics_substeps,
        )
        for v in self.vehicles:
            v.anchor(track, self.time)
            v.controller.reset(make_track_info(track))
        self._dynamics.warmup(len(self.vehicles))

    def _grid_pose(self, index: int) -> tuple[float, float, float]:
        s = (
            self.track.track_length - (index + 1) * _GRID_ROW
        ) % self.track.track_length
        if index == 0:
            lateral = 0.0
        elif index % 2 == 1:
            lateral = -_GRID_OFFSET
        else:
            lateral = _GRID_OFFSET
        return self.track.to_cartesian(s, lateral)

    def _release(self) -> None:
        """Re-anchor the lap trackers at the grid poses on release."""
        for v in self.vehicles:
            v.anchor(self.track, self.time)

    @property
    def finished(self) -> bool:
        """True once every vehicle has finished or DNF'd."""
        return all(v.state.status in _TERMINAL for v in self.vehicles)

    @property
    def phase(self) -> str:
        """Race phase: "waiting", "countdown", "racing", or "finished"."""
        if self._waiting:
            return "waiting"
        if self._countdown_left > 0:
            return "countdown"
        return "racing" if not self.finished else "finished"

    @property
    def countdown(self) -> float:
        """Countdown time remaining, in seconds (0.0 once released)."""
        return self._countdown_left * self._dt

    @property
    def last_scans(self) -> list[np.ndarray | None]:
        """Each vehicle's last computed laser scan, in vehicle order."""
        return self._last_scans

    @property
    def results(self) -> RaceResult:
        """The race results, ranked; valid once the race is finished."""
        return self._results()

    def start(self) -> None:
        """Release the waiting field: countdown or immediate racing."""
        self._waiting = False

    def tick(self) -> None:
        """Advance the race by one tick (1/40 s); a no-op while waiting."""
        if self._waiting:
            return
        self.time += self._dt
        if self._countdown_left > 0:
            self._countdown_left -= 1
            if self._countdown_left == 0:
                self._release()
            return
        self._step_controllers()
        self._integrate()
        self._advance_timers()
        self._check_crashes()
        self._book_laps()
        self._check_timeout()

    def run(self) -> RaceResult:
        """Run the race to completion and return the results."""
        self.start()
        while not self.finished:
            self.tick()
        return self.results

    def snapshot(self) -> RaceSnapshot:
        """Build a read-only snapshot of the current race state."""
        return RaceSnapshot(
            time=self.time,
            track=self.track,
            vehicles=tuple(
                VehicleSnapshot(
                    name=v.name,
                    id=i,
                    status=v.state.status,
                    x=v.x,
                    y=v.y,
                    yaw=v.yaw,
                    speed=v.speed,
                    steering=v.steering,
                    laps_completed=v.state.laps_completed,
                    best_lap=v.state.best_lap,
                    last_lap=v.state.last_lap,
                    crashes=v.state.crashes,
                    finish_time=v.state.finish_time,
                    dnf_reason=v.state.dnf_reason,
                    last_crash=v.last_crash,
                )
                for i, v in enumerate(self.vehicles)
            ),
        )

    def _active(self) -> list[Vehicle]:
        return [v for v in self.vehicles if v.state.status not in _TERMINAL]

    def _step_controllers(self) -> None:
        stepped = [v for v in self.vehicles if v.state.may_step]
        if not stepped:
            return
        scans = fleet_scan(
            self.track, stepped, self._beam_angles, self._collision_distance
        )
        k = 0
        for i, v in enumerate(self.vehicles):
            if v.state.may_step:
                self._last_scans[i] = scans[k]
                k += 1
        for v, scan in zip(stepped, scans, strict=True):
            speed, steering = v.controller.step(
                v.x, v.y, v.yaw, v.speed, v.steering, scan
            )
            v.target_speed = float(speed)
            v.target_steering = float(steering)

    def _integrate(self) -> None:
        active = self._active()
        if not active:
            return
        states = np.array([[v.x, v.y, v.yaw, v.speed, v.steering] for v in active])
        commands = np.array([[v.target_speed, v.target_steering] for v in active])
        stepped = self._dynamics.step(states, commands)
        for v, row in zip(active, stepped, strict=True):
            v.x, v.y, v.yaw, v.speed, v.steering = map(float, row)

    def _advance_timers(self) -> None:
        for v in self.vehicles:
            v.state.advance()

    def _check_crashes(self) -> None:
        crashed = collide(
            self.track,
            self.vehicles,
            self._length,
            self._width,
            self._collision_distance,
        )
        for v in crashed:
            v.crash(self.track)

    def _book_laps(self) -> None:
        for v in self._active():
            v.record(self.track, self.time)

    def _check_timeout(self) -> None:
        if self.time < self._time_limit:
            return
        for v in self._active():
            v.state.timeout()

    def _results(self) -> RaceResult:
        finishers = sorted(
            (v for v in self.vehicles if v.state.status is VehicleStatus.FINISHED),
            key=lambda v: (v.state.finish_time, v.name),
        )
        dnfs = sorted(
            (v for v in self.vehicles if v.state.status is VehicleStatus.DNF),
            key=lambda v: v.name,
        )
        results = [
            self._vehicle_result(v, order) for order, v in enumerate(finishers, 1)
        ]
        results.extend(self._vehicle_result(v, None) for v in dnfs)
        return RaceResult(track_name=self.track.name, time=self.time, results=results)

    @staticmethod
    def _vehicle_result(v: Vehicle, order: int | None) -> VehicleResult:
        return VehicleResult(
            name=v.name,
            status=v.state.status,
            finish_order=order,
            total_time=v.state.finish_time,
            best_lap=v.state.best_lap,
            last_lap=v.state.last_lap,
            laps_completed=v.state.laps_completed,
            crashes=v.state.crashes,
            dnf_reason=v.state.dnf_reason,
        )


def run_race(
    track: Track,
    config: Config,
    controllers: list[Controller],
    names: list[str] | None = None,
    mode: str = "time-trial",
) -> RaceResult:
    """Run a full headless race and return the results.

    The deterministic entry point of the engine: no wall clock, no
    threads, no web. In time-trial mode every vehicle starts at the
    track's start pose; in race mode the field starts on the hardcoded
    zigzag grid behind the start/finish line and is released after the
    countdown.
    """
    return RaceEngine(track, config, controllers, names, mode=mode).run()
