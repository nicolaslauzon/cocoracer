"""Per-vehicle record: controller, race state, lap tracker, pose, motion,
and the vehicle's position on the centerline: anchor, per-tick lap
recording, and the crash consequence."""

from dataclasses import dataclass

from cocoracer.controller import Controller
from cocoracer.lap_tracker import LapTracker
from cocoracer.race_state import RaceState
from cocoracer.track import Track


@dataclass
class Vehicle:
    """Per-vehicle state observed at the engine seam."""

    name: str
    controller: Controller
    state: RaceState
    tracker: LapTracker
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    speed: float = 0.0
    steering: float = 0.0
    target_speed: float = 0.0
    target_steering: float = 0.0

    def anchor(self, track: Track, time: float) -> None:
        """Re-anchor the lap tracker at the current pose and time.

        Called when the race starts and again when the countdown
        releases, so the first lap is timed from the release.
        """
        s, _, _ = track.to_frenet(self.x, self.y, self.yaw)
        self.tracker.start(s, time)

    def record(self, track: Track, time: float) -> None:
        """Feed the lap tracker at the current pose, once per tick.

        Only RACING vehicles are fed; a booking goes to the race state,
        which may finish the vehicle.
        """
        if not self.state.is_racing:
            return
        s, _, _ = track.to_frenet(self.x, self.y, self.yaw)
        lap_time = self.tracker.feed(s, time)
        if lap_time is not None:
            self.state.record_lap(lap_time, time)

    def crash(self, track: Track) -> bool:
        """Apply the crash consequence; True if the crash DNFs the vehicle.

        Zeroes the motion, registers the crash with the race state (pause,
        or DNF at the crash limit), and — unless it is a DNF — resets the
        vehicle to the nearest centerline pose with the lap tracker
        resynced there.
        """
        dnf = self.state.crash()
        self.speed = 0.0
        self.steering = 0.0
        self.target_speed = 0.0
        self.target_steering = 0.0
        if not dnf:
            x, y, yaw = track.nearest_centerline(self.x, self.y)
            self.x, self.y, self.yaw = x, y, yaw
            s, _, _ = track.to_frenet(self.x, self.y, self.yaw)
            self.tracker.resync(s)
        return dnf
