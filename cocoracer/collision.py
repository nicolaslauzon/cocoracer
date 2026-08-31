"""Batched crash detection: walls first, then racing vehicle pairs with fault.

Each racing vehicle takes at most one crash per tick: a vehicle whose
footprint touches a wall is out of the vehicle-to-vehicle pass, and a vehicle
already reported drops out of later pairs. Ghosts and paused vehicles neither
hit nor are hit. For a pair within the collision distance the fault rule
returns only the instigator(s): the vehicle whose closing velocity toward the
other is larger, or both on a mutual (head-on / stationary overlap) contact.
"""

import math

from cocoracer.track import Track
from cocoracer.vehicle import Vehicle

_FAULT_ZERO_CLOSING = 1e-2
_FAULT_TIE = 1e-6


def _velocity(v: Vehicle) -> tuple[float, float]:
    """The vehicle's velocity vector, from its speed and heading."""
    return (v.speed * math.cos(v.yaw), v.speed * math.sin(v.yaw))


def _pair_fault(a: Vehicle, b: Vehicle) -> tuple[bool, bool]:
    """Which of (a, b) is at fault; (True, True) on a mutual contact."""
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist == 0.0:
        return True, True
    ux, uy = dx / dist, dy / dist
    vx_a, vy_a = _velocity(a)
    vx_b, vy_b = _velocity(b)
    closing_a = vx_a * ux + vy_a * uy
    closing_b = vx_b * -ux + vy_b * -uy
    if abs(closing_a) < _FAULT_ZERO_CLOSING and abs(closing_b) < _FAULT_ZERO_CLOSING:
        return True, True
    if abs(closing_a - closing_b) < _FAULT_TIE:
        return True, True
    if closing_a > closing_b:
        return True, False
    return False, True


def collide(
    track: Track,
    fleet: list[Vehicle],
    length: float,
    width: float,
    collision_distance: float,
) -> list[Vehicle]:
    """The vehicles that crash this tick and are penalized, in crash order.

    Args:
        track: The track whose occupancy grid is checked.
        fleet: All the vehicles in the race.
        length: Vehicle length in meters, for the wall footprint check.
        width: Vehicle width in meters, for the wall footprint check.
        collision_distance: Center-to-center distance below which two
            racing vehicles crash.

    Returns:
        The penalized vehicles: wall hits first in fleet order, then pair hits
        in pair order (the lower fleet index first). For a vehicle-to-vehicle
        pair only the instigator is returned — the vehicle whose closing
        velocity toward the other is larger — unless the contact is mutual
        (head-on or stationary overlap), when both are returned. Each vehicle
        appears at most once.
    """
    crashed: list[Vehicle] = []
    done: set[int] = set()
    racing = [v for v in fleet if v.state.is_racing]
    for v in racing:
        if track.footprint_in_wall(v.x, v.y, v.yaw, length, width):
            crashed.append(v)
            done.add(id(v))
    pool = [v for v in racing if id(v) not in done]
    for i in range(len(pool)):
        a = pool[i]
        if id(a) in done:
            continue
        for j in range(i + 1, len(pool)):
            b = pool[j]
            if id(b) in done:
                continue
            if math.hypot(a.x - b.x, a.y - b.y) >= collision_distance:
                continue
            fault_a, fault_b = _pair_fault(a, b)
            if fault_a and id(a) not in done:
                crashed.append(a)
                done.add(id(a))
            if fault_b and id(b) not in done:
                crashed.append(b)
                done.add(id(b))
    return crashed
