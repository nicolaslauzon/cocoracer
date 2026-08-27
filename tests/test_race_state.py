"""Tests for the per-vehicle race record (RaceState)."""

import dataclasses

from cocoracer.race_state import DnfReason, RaceState, VehicleStatus


def _state() -> RaceState:
    return RaceState(pause_ticks=20, ghost_ticks=60, max_crashes=5, laps_target=3)


def test_crash_cycle_is_twenty_pause_then_sixty_ghost() -> None:
    state = _state()
    assert state.status is VehicleStatus.RACING
    assert state.crash() is False
    assert state.status is VehicleStatus.PAUSED
    statuses: list[VehicleStatus] = []
    for _ in range(20):
        state.advance()
        statuses.append(state.status)
    for _ in range(60):
        state.advance()
        statuses.append(state.status)
    assert statuses[:19] == [VehicleStatus.PAUSED] * 19
    assert statuses[19:79] == [VehicleStatus.GHOST] * 60
    assert statuses[79] is VehicleStatus.RACING
    assert state.crashes == 1


def test_advance_is_a_noop_outside_pause_and_ghost() -> None:
    state = _state()
    state.advance()
    assert state.status is VehicleStatus.RACING
    state.timeout()
    state.advance()
    assert state.status is VehicleStatus.DNF


def test_crash_dnfs_at_crash_limit() -> None:
    state = dataclasses.replace(_state(), max_crashes=2)
    assert state.crash() is False
    assert state.status is VehicleStatus.PAUSED
    assert state.crash() is True
    assert state.status is VehicleStatus.DNF
    assert state.dnf_reason is DnfReason.MAX_CRASHES
    assert state.crashes == 2


def test_timeout_dnfs_with_timeout_reason() -> None:
    state = _state()
    state.timeout()
    assert state.status is VehicleStatus.DNF
    assert state.dnf_reason is DnfReason.TIMEOUT


def test_record_lap_updates_best_and_last_and_finishes_at_target() -> None:
    state = dataclasses.replace(_state(), laps_target=2)
    state.record_lap(12.0, 12.0)
    assert state.laps_completed == 1
    assert state.last_lap == 12.0
    assert state.best_lap == 12.0
    assert state.status is VehicleStatus.RACING
    assert state.finish_time is None
    state.record_lap(11.0, 23.0)
    assert state.laps_completed == 2
    assert state.last_lap == 11.0
    assert state.best_lap == 11.0
    assert state.status is VehicleStatus.FINISHED
    assert state.finish_time == 23.0


def test_may_step_is_racing_or_ghost_and_is_racing_is_racing_only() -> None:
    state = _state()
    assert state.may_step is True
    assert state.is_racing is True
    state.crash()
    assert state.may_step is False
    assert state.is_racing is False
    for _ in range(20):
        state.advance()
    assert state.status is VehicleStatus.GHOST
    assert state.may_step is True
    assert state.is_racing is False
    for _ in range(60):
        state.advance()
    assert state.status is VehicleStatus.RACING
    assert state.may_step is True
    assert state.is_racing is True
    state.timeout()
    assert state.may_step is False
    assert state.is_racing is False
    finished = _state()
    for _ in range(3):
        finished.record_lap(10.0, 10.0)
    assert finished.status is VehicleStatus.FINISHED
    assert finished.may_step is False
    assert finished.is_racing is False
