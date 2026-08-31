# 01: Instigator-only fault attribution

**What to build:** crash detection stops penalizing everyone who touches. When
two racing vehicles close within the collision distance, only the car that
caused the collision is penalized — the one whose closing velocity toward the
other is larger. A rear-end penalizes only the follower, a side-swipe or T-bone
only the crossing car, and a head-on or stationary overlap (no clear
instigator) penalizes both as before. Wall hits are always self-fault, each
vehicle is penalized at most once per tick, and in a pile a car at fault in even
one pair is the instigator while an only-victim is penalized by no pair.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] `collide()` returns only the vehicles to penalize: wall hits always; a
      racing pair under the collision distance yields the sole instigator, or
      both on a mutual (head-on / near-stationary) contact.
- [ ] A rear-end returns only the follower; a side-swipe returns only the
      crossing car.
- [ ] A head-on or stationary overlap returns both cars.
- [ ] A wall hit beats being a pair instigator in the same tick and is returned
      once.
- [ ] One crash per tick: a vehicle consumed by the wall pass or an earlier pair
      drops out of later pairs.
- [ ] In a pile, each instigator is returned once and an only-victim is returned
      by no pair (kept racing).