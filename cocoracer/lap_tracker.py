"""Lap-counting machine: start/finish line plus mid-track checkpoint."""


class LapTracker:
    """Books a lap when the start/finish line is crossed after the checkpoint."""

    def __init__(self, track_length: float, checkpoint_s: float) -> None:
        self._track_length = track_length
        self._checkpoint_s = checkpoint_s
        self._prev_s = 0.0
        self._checkpoint_passed = False
        self._lap_start = 0.0

    def start(self, s: float, time: float) -> None:
        """Anchor the tracker at the race start pose and time."""
        self._prev_s = s
        self._checkpoint_passed = False
        self._lap_start = time

    def resync(self, s: float) -> None:
        """Re-anchor after a crash reset so the jump is not read as a lap."""
        self._prev_s = s

    def feed(self, s: float, time: float) -> float | None:
        """Feed the current arc length; the lap time if one was booked."""
        prev = self._prev_s
        if prev < self._checkpoint_s <= s and (s - prev) < self._checkpoint_s:
            self._checkpoint_passed = True
        lap_time: float | None = None
        if (
            prev >= self._checkpoint_s
            and s < self._checkpoint_s
            and (s + self._track_length - prev) < self._checkpoint_s
            and self._checkpoint_passed
        ):
            self._checkpoint_passed = False
            lap_time = time - self._lap_start
            self._lap_start = time
        self._prev_s = s
        return lap_time
