"""Per-vehicle race record: status, crash/pause/ghost timers, laps, DNF."""

import enum
from dataclasses import dataclass


class VehicleStatus(enum.Enum):
    RACING = "racing"
    PAUSED = "paused"
    GHOST = "ghost"
    FINISHED = "finished"
    DNF = "dnf"


class DnfReason(enum.Enum):
    TIMEOUT = "timeout"
    MAX_CRASHES = "max crashes"


@dataclass
class RaceState:
    """Per-vehicle race record: status, timers, crashes, laps, finish."""

    pause_ticks: int
    ghost_ticks: int
    max_crashes: int
    laps_target: int
    status: VehicleStatus = VehicleStatus.RACING
    crashes: int = 0
    laps_completed: int = 0
    best_lap: float | None = None
    last_lap: float | None = None
    finish_time: float | None = None
    dnf_reason: DnfReason | None = None
    _pause_left: int = 0
    _ghost_left: int = 0

    @property
    def may_step(self) -> bool:
        return self.status in (VehicleStatus.RACING, VehicleStatus.GHOST)

    @property
    def is_racing(self) -> bool:
        return self.status is VehicleStatus.RACING

    def advance(self) -> None:
        if self.status is VehicleStatus.PAUSED:
            self._pause_left -= 1
            if self._pause_left <= 0:
                self.status = VehicleStatus.GHOST
                self._ghost_left = self.ghost_ticks
        elif self.status is VehicleStatus.GHOST:
            self._ghost_left -= 1
            if self._ghost_left <= 0:
                self.status = VehicleStatus.RACING

    def crash(self) -> bool:
        """Register a crash; True if it DNFs the vehicle at the crash limit."""
        self.crashes += 1
        if self.crashes >= self.max_crashes:
            self.status = VehicleStatus.DNF
            self.dnf_reason = DnfReason.MAX_CRASHES
            return True
        self.status = VehicleStatus.PAUSED
        self._pause_left = self.pause_ticks
        return False

    def timeout(self) -> None:
        self.status = VehicleStatus.DNF
        self.dnf_reason = DnfReason.TIMEOUT

    def record_lap(self, lap_time: float, time: float) -> None:
        self.laps_completed += 1
        self.last_lap = lap_time
        if self.best_lap is None or lap_time < self.best_lap:
            self.best_lap = lap_time
        if self.laps_completed >= self.laps_target:
            self.status = VehicleStatus.FINISHED
            self.finish_time = time
