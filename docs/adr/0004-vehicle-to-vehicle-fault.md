# Penalize only the instigator in a vehicle-to-vehicle crash

Before this decision, any two racing vehicles closer than the collision
distance both crashed: each took a pause, a crash count toward its DNF limit,
and a centerline reset, regardless of who caused the contact. A car that was
rear-ended, or clipped from the side while holding its line, was penalized
exactly like the car that hit it. There was no notion of fault in the sim.

Now fault is attributed per collision. In a racing pair within the collision
distance, the vehicle whose closing velocity toward the other is larger is the
sole instigator and is the only one penalized. A head-on or stationary
overlap, where neither closing speed dominates, is mutual and both are
penalized as before. A wall hit is always self-fault and beats being a pair
instigator in the same tick; each vehicle is penalized at most once per tick,
and an only-victim in a pile rides out untouched.

## Considered options

- **Symmetric (status quo)**: simple and predictable, but penalizes the victim
  of a rear-end or side-swipe; a player who gets hit loses like the hitter.
- **Fault from velocities** (chosen): the closing-velocity comparison reads
  clearly as "who drove into whom", handles rear-ends (follower at fault),
  side-swipes and T-bones (the crossing car at fault), and degrades to mutual
  for head-ons and stationary overlaps. The instigator then flows through the
  engine's existing crash path unchanged, so no new invulnerability rules are
  needed — the pause→ghost→racing sequence already keeps it out of collisions
  in the next tick.
- **Fault from contact geometry**: a more "physical" blame, but the engine has
  no contact-point or surface geometry at the tick boundary, so it would need
  new computation for little gain over the velocity rule.

## Consequences

- `collision.collide()` no longer returns every contactor — it returns only the
  vehicles to penalize. The engine crashes exactly what `collide()` returns, so
  the reverse is true for the innocent: it is not in the return list, its
  `crashes` counter, `last_crash`, status, and pose all stay put, and it just
  keeps racing.
- Because the victim no longer absorbs a crash, vehicle-to-vehicle contact
  changes a race's *result*: side-swipes and rear-ends no longer cost the
  innocent a crash toward its DNF limit.
- The rule only picks *which* car is penalized; it does not change the
  collision distance, pause, ghost, or DNF parameters, nor the wall-crash path.