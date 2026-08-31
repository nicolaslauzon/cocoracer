# cocoracer

A single-player game in which the player programs the autonomous controller for
an Ackermann vehicle in one Python file and races it on closed-loop tracks
against built-in baselines and other controllers.

## Language

**Track**:
A closed-loop racing surface defined by a centerline, two wall boundaries
of variable width between them, and a wall occupancy grid.
_Avoid_: level, course, circuit

**Map**:
A PGM image a track is built from: white pixels are the drivable surface,
every other color is wall.
_Avoid_: image, picture, png

**Centerline**:
The one-dimensional spine of a track; arc length, the start/finish line, and
Frenet offsets are all measured along it.
_Avoid_: spine, path, route

**Wall**:
The boundary of a track; driving past it is a crash.
_Avoid_: barrier, curb, limit

**Frenet coordinates**:
A point's position relative to the centerline: arc length `s`, lateral offset
`d`, and heading error.
_Avoid_: track frame, local frame

**Controller**:
The player's single-file driving code: one class with a `reset` and a per-tick
`step` that turns a state and a laser scan into a target speed and steering
angle.
_Avoid_: driver, bot, AI, agent

**Baseline**:
A built-in reference controller that ships with the game and can be raced
against.
_Avoid_: AI, bot, opponent, agent

**Tick**:
One fixed-rate iteration of the race loop, in which every controller that may
be stepped (racing or ghost) is stepped exactly once.
_Avoid_: step, frame, iteration

**Laser scan**:
The full-circle array of beam distances handed to a controller each tick; a
beam that hits nothing reads as no-hit rather than a max range.
_Avoid_: lidar, sensor, rays

**Ghost**:
The post-crash state in which a vehicle is invisible to laser scans and cannot
be collided with; the controller is still stepped, and the vehicle passes
through walls, lasting a fixed duration.
_Avoid_: phantom, invincible, safe

**Pause**:
The post-crash state in which a vehicle holds still producing no output and its
controller is not consulted, lasting a fixed duration.
_Avoid_: freeze, stun, reset

**Waiting**:
The pre-start state in which the field is set and the sim clock is frozen
until the race is started.
_Avoid_: lobby, armed, pre-race

**Crash**:
The event of a racing vehicle touching a wall, or closing within the collision
distance of another racing vehicle as the instigator; the vehicle's motion is
zeroed and it takes a pause, or a DNF at the crash limit, and unless it is a DNF
it is reset to the nearest centerline pose. In a vehicle-to-vehicle collision
only the instigator incurs this penalty; the innocent vehicle is untouched.
_Avoid_: accident, wreck, spin

**Instigator**:
The vehicle at fault in a vehicle-to-vehicle collision, decided per pair by
which vehicle's closing velocity toward the other is larger; a head-on or
stationary overlap is mutual and both are instigators. The innocent party keeps
racing with no penalty.
_Avoid_: culprit, at-fault car, aggressor

**Time trial**:
A race mode in which one controller races alone for a fixed lap count.
_Avoid_: solo, practice, qualification

**Head-to-head**:
A race mode between exactly two controllers.
_Avoid_: duel, match, 1v1

**Starting grid**:
The staggered line of poses behind the start/finish line from which a
multi-vehicle race begins (not the wall's storage grid).
_Avoid_: grid, formation

**Checkpoint**:
The mid-track line that, together with the start/finish line, validates a lap.
_Avoid_: mid-line, gate, split

**DNF**:
Did-not-finish: a vehicle that exceeds the crash limit or the race time limit.
_Avoid_: crash-out, failure
