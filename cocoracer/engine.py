"""Deterministic headless race engine.

One single-threaded fixed-step loop (40 Hz). Per tick, in order: racing
controllers are stepped, commands are integrated by the batched JAX
dynamics, crash timers advance, wall collisions are checked against the
track's occupancy grid with the vehicle footprint, crash handling runs
(reset to the nearest centerline pose, pause, ghost), and laps are
booked behind the start/finish line plus mid-track checkpoint.
"""

import enum
from dataclasses import dataclass

import numpy as np

from cocoracer.config import Config
from cocoracer.controller import Controller, make_track_info
from cocoracer.dynamics import Dynamics, DynamicsParams, pack_state
from cocoracer.track import Track


class VehicleStatus(enum.Enum):
    RACING = "racing"
    PAUSED = "paused"
    GHOST = "ghost"
    FINISHED = "finished"
    DNF = "dnf"


class DnfReason(enum.Enum):
    TIMEOUT = "timeout"
    MAX_CRASHES = "max crashes"


_TERMINAL = (VehicleStatus.FINISHED, VehicleStatus.DNF)


@dataclass
class Vehicle:
    """Per-vehicle state observed at the engine seam."""

    name: str
    controller: Controller
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    speed: float = 0.0
    steering: float = 0.0
    status: VehicleStatus = VehicleStatus.RACING
    laps_completed: int = 0
    crashes: int = 0
    best_lap: float | None = None
    last_lap: float | None = None
    finish_time: float | None = None
    dnf_reason: DnfReason | None = None
    target_speed: float = 0.0
    target_steering: float = 0.0
    _pause_left: int = 0
    _ghost_left: int = 0
    _checkpoint_passed: bool = False
    _prev_s: float = 0.0
    _lap_start: float = 0.0

    @property
    def is_racing(self) -> bool:
        return self.status is VehicleStatus.RACING


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


class RaceEngine:
    """Fixed-step deterministic race simulation for one track."""

    def __init__(
        self,
        track: Track,
        config: Config,
        controllers: list[Controller],
        names: list[str] | None = None,
    ) -> None:
        if not controllers:
            raise ValueError("at least one controller is required")
        if names is None:
            names = [f"vehicle{i + 1}" for i in range(len(controllers))]
        if len(names) != len(controllers):
            raise ValueError("names and controllers must have the same length")
        self.track = track
        self.config = config
        self.time = 0.0
        x, y, yaw = track.start_pose
        self.vehicles = [
            Vehicle(name=name, controller=ctl, x=x, y=y, yaw=yaw)
            for name, ctl in zip(names, controllers, strict=True)
        ]
        self._dt = config.sim.tick_dt
        self._laps = config.race.laps
        self._time_limit = config.race.time_limit
        self._pause_ticks = int(round(config.race.crash_pause / self._dt))
        self._ghost_ticks = int(round(config.race.ghost_duration / self._dt))
        self._max_crashes = config.race.max_crashes
        self._length = config.vehicle.length
        self._width = config.vehicle.width
        self._dynamics = Dynamics(
            DynamicsParams.from_config(
                config.vehicle, config.sim.tick_dt, config.sim.physics_substeps
            ),
            config.sim.physics_substeps,
        )
        for v in self.vehicles:
            v._prev_s, _, _ = track.to_frenet(v.x, v.y, v.yaw)
            v.controller.reset(make_track_info(track))
        self._dynamics.warmup(len(self.vehicles))

    def tick(self) -> None:
        """Advance the race by one tick (1/40 s)."""
        self.time += self._dt
        self._step_controllers()
        self._integrate()
        self._advance_timers()
        self._check_walls()
        self._book_laps()
        self._check_timeout()

    def run(self) -> RaceResult:
        """Run the race to completion and return the results."""
        while any(v.status not in _TERMINAL for v in self.vehicles):
            self.tick()
        return self._results()

    def _active(self) -> list[Vehicle]:
        return [v for v in self.vehicles if v.status not in _TERMINAL]

    def _step_controllers(self) -> None:
        for v in self.vehicles:
            if not v.is_racing:
                continue
            speed, steering = v.controller.step(v.x, v.y, v.yaw, v.speed, v.steering)
            v.target_speed = float(speed)
            v.target_steering = float(steering)

    def _integrate(self) -> None:
        active = self._active()
        if not active:
            return
        states = np.array(
            [
                pack_state(
                    v.x,
                    v.y,
                    v.yaw,
                    v.speed,
                    v.steering,
                    v.target_speed,
                    v.target_steering,
                )
                for v in active
            ]
        )
        stepped = self._dynamics.step(states)
        for v, row in zip(active, stepped, strict=True):
            v.x, v.y, v.yaw, v.speed, v.steering = map(float, row[:5])

    def _advance_timers(self) -> None:
        for v in self.vehicles:
            if v.status is VehicleStatus.PAUSED:
                v._pause_left -= 1
                if v._pause_left <= 0:
                    v.status = VehicleStatus.GHOST
                    v._ghost_left = self._ghost_ticks
            elif v.status is VehicleStatus.GHOST:
                v._ghost_left -= 1
                if v._ghost_left <= 0:
                    v.status = VehicleStatus.RACING

    def _check_walls(self) -> None:
        for v in self.vehicles:
            if not v.is_racing:
                continue
            if self.track.footprint_in_wall(v.x, v.y, v.yaw, self._length, self._width):
                self._handle_crash(v)

    def _handle_crash(self, v: Vehicle) -> None:
        v.crashes += 1
        v.speed = 0.0
        v.steering = 0.0
        v.target_speed = 0.0
        v.target_steering = 0.0
        if v.crashes >= self._max_crashes:
            v.status = VehicleStatus.DNF
            v.dnf_reason = DnfReason.MAX_CRASHES
            return
        x, y, yaw = self.track.nearest_centerline(v.x, v.y)
        v.x, v.y, v.yaw = x, y, yaw
        v.status = VehicleStatus.PAUSED
        v._pause_left = self._pause_ticks
        v._prev_s, _, _ = self.track.to_frenet(v.x, v.y, v.yaw)

    def _book_laps(self) -> None:
        length = self.track.track_length
        half = length / 2.0
        for v in self._active():
            s, _, _ = self.track.to_frenet(v.x, v.y, v.yaw)
            prev = v._prev_s
            if prev < half <= s and (s - prev) < half:
                v._checkpoint_passed = True
            if prev >= half and s < half and (s + length - prev) < half:
                if v._checkpoint_passed and v.is_racing:
                    v._checkpoint_passed = False
                    lap_time = self.time - v._lap_start
                    v.laps_completed += 1
                    v.last_lap = lap_time
                    if v.best_lap is None or lap_time < v.best_lap:
                        v.best_lap = lap_time
                    v._lap_start = self.time
                    if v.laps_completed >= self._laps:
                        v.status = VehicleStatus.FINISHED
                        v.finish_time = self.time
            v._prev_s = s

    def _check_timeout(self) -> None:
        if self.time < self._time_limit:
            return
        for v in self._active():
            v.status = VehicleStatus.DNF
            v.dnf_reason = DnfReason.TIMEOUT

    def _results(self) -> RaceResult:
        finishers = sorted(
            (v for v in self.vehicles if v.status is VehicleStatus.FINISHED),
            key=lambda v: (v.finish_time, v.name),
        )
        dnfs = sorted(
            (v for v in self.vehicles if v.status is VehicleStatus.DNF),
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
            status=v.status,
            finish_order=order,
            total_time=v.finish_time,
            best_lap=v.best_lap,
            last_lap=v.last_lap,
            laps_completed=v.laps_completed,
            crashes=v.crashes,
            dnf_reason=v.dnf_reason,
        )


def run_race(
    track: Track,
    config: Config,
    controllers: list[Controller],
    names: list[str] | None = None,
) -> RaceResult:
    """Run a full headless race and return the results.

    The deterministic entry point of the engine: no wall clock, no
    threads, no web. Every vehicle starts at the track's start pose.
    """
    return RaceEngine(track, config, controllers, names).run()
