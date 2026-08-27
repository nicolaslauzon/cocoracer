"""Tests for the lap-counting machine (LapTracker)."""

from cocoracer.lap_tracker import LapTracker

LENGTH = 20.0
CHECKPOINT = 10.0


def test_monotone_s_sequence_books_lap_with_lap_time() -> None:
    tracker = LapTracker(track_length=LENGTH, checkpoint_s=CHECKPOINT)
    tracker.start(0.0, 0.0)
    booked: list[float] = []
    for i in range(1, 81):
        s = (i * 0.5) % LENGTH
        lap = tracker.feed(s, i * 0.25)
        if lap is not None:
            booked.append(lap)
    assert booked == [10.0, 10.0]


def test_oscillation_across_start_line_without_checkpoint_books_no_lap() -> None:
    tracker = LapTracker(track_length=LENGTH, checkpoint_s=CHECKPOINT)
    tracker.start(19.5, 0.0)
    pattern = (0.0, 0.5, 0.0, 19.5)
    for i in range(1, 41):
        assert tracker.feed(pattern[i % 4], i * 0.1) is None


def test_resync_after_crash_reset_books_no_spurious_lap() -> None:
    tracker = LapTracker(track_length=LENGTH, checkpoint_s=CHECKPOINT)
    tracker.start(0.0, 0.0)
    for i in range(1, 40):
        assert tracker.feed(i * 0.5, i * 0.1) is None
    # Crash reset: the car jumps from 19.5 (checkpoint flagged) to just
    # past the start line, which must not book the half lap.
    tracker.resync(0.1)
    assert tracker.feed(0.1, 4.0) is None
    booked: list[float] = []
    for i in range(1, 41):
        s = (0.1 + i * 0.5) % LENGTH
        lap = tracker.feed(s, 4.0 + i * 0.05)
        if lap is not None:
            booked.append(lap)
    assert booked == [6.0]
