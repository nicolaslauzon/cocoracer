"""Batched crash detection: walls first, then racing vehicle pairs.

Each racing vehicle takes at most one crash per tick: a vehicle whose
footprint touches a wall is out of the vehicle-to-vehicle pass, and a
vehicle already reported by an earlier pair drops out of the later
ones. Ghosts and paused vehicles neither hit nor are hit.
"""

import math

from cocoracer.track import Track
from cocoracer.vehicle import Vehicle


def collide(
    track: Track,
    fleet: list[Vehicle],
    length: float,
    width: float,
    collision_distance: float,
) -> list[Vehicle]:
    """Racing vehicles that crash this tick, in crash order.

    Args:
        track: The track whose occupancy grid is checked.
        fleet: All the vehicles in the race.
        length: Vehicle length in meters, for the wall footprint check.
        width: Vehicle width in meters, for the wall footprint check.
        collision_distance: Center-to-center distance below which two
            racing vehicles crash.

    Returns:
        The crashed vehicles: wall hits first in fleet order, then
        vehicle-to-vehicle hits in pair order (the lower fleet index
        first). Each vehicle appears at most once.
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
            if math.hypot(a.x - b.x, a.y - b.y) < collision_distance:
                crashed.append(a)
                crashed.append(b)
                done.add(id(a))
                done.add(id(b))
    return crashed
