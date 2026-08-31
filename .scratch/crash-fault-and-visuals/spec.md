Status: done

# Spec: Crash fault attribution + live-view trail, crash Xs, and picture-true map

## Problem Statement

Two cars that collide are both penalized today: crossing the collision
distance crashes whichever two vehicles are involved, regardless of who caused
it. A car that is rear-ended, or that is clipped from the side while it holds
its line, is yanked out of the race just like the car that hit it — its
crash counter, pause, and DNF bank roll up as if the collision were its fault.
There is no notion of an instigator anywhere in the sim.

Meanwhile the live view does not read the way the player expects. The colored
path behind a vehicle is drawn as a series of short stroked segments with round
caps and per-segment fading, so it renders as separate circles at the recorded
poses rather than a solid line. Crash X marks are small and are not rendered
conspicuously for vehicle-to-vehicle collisions, so after a car-on-car crash
there is no visible mark where it happened. And the map layer the player looks
at is the display `-gimp` image (white road, wall outlines drawn in), while the
physics and laser scan run on the clean base image — on two of the three maps
these differ, so what the player sees disagrees with what the car actually
hits.

## Solution

Adopt per-collision fault attribution: when two racing vehicles collide, the
vehicle that caused the collision is penalized; the other keeps racing,
completely untouched. Fault is decided per pair from the closing velocities:
the vehicle whose closing velocity toward the other is larger is the
instigator. Ties and near-zero closing (head-on or stationary overlap) are
mutual — both are penalized as today. An instigator that is also touching a wall
in the same tick is treated as a wall crash (self-fault). A vehicle can be
penalized at most once per tick regardless of how many vehicles it is touching.
The innocent vehicle rides out the tick unchanged: no crash counter, no pause,
no ghost, no X, no DNF — it simply keeps racing from its existing pose.

The live view is tightened to match the player's mental model. The trail is a
single continuous solid line in the vehicle's color with the tail fade
preserved (the trailing end still dims out, but the body is one clean stroke
instead of stacked circles). Crash X marks are drawn at 2× their current size,
in the crashing vehicle's identity color, for both wall and vehicle-to-vehicle
collisions, and each vehicle shows only its single most-recent crash. The map
layer is the image the laser scan and collisions are computed from — the base
image, not the decorative `-gimp` variant — so what you see is exactly the
picture the car races on.

## User Stories

1. As a player, I want the car that rear-ends another to be the one penalized,
   so that getting hit from behind does not cost me the race.
2. As a player, I want a car that is clipped from the side while holding its
   line to keep racing, so that a T-bone I didn't cause does not reset me.
3. As a player, I want a head-on or a stationary overlap to penalize both cars,
   so that a collision with no clear instigator is still settled.
4. As a player, I want a wall crash to count for the wall-hitter even if it also
   touched another car that tick, so that nobody else inherits my wall hit.
5. As a player, I want to be penalized at most once per tick no matter how many
   cars I clip at once, so that a pile-up does not stack several crashes on me.
6. As a player, I want the innocent car to be completely untouched — same crash
   count, same position, still racing — so that the penalty lands only where it
   belongs.
7. As a player, I want a vehicle's drawn path to be a solid line in its color,
   so that the racing line reads as a continuous ribbon rather than a string of
   dots.
8. As a player, I want the path's tail to still fade into the distance, so that
   the trail stays legible on a long track even as it recedes.
9. As a player, I want crash X marks twice as big as they are now, so that I can
   actually pick them out on the map.
10. As a player, I want crash X marks drawn for vehicle-to-vehicle collisions
    too, so that a car-on-car crash leaves evidence where it happened.
11. As a player, I want each crash X in the crashing vehicle's own color, so
    that I can tell at a glance which car crashed where.
12. As a player, I want each vehicle to show only its most-recent crash X, so
    that the map does not fill with old crash scars over a full race.
13. As a player, I want the map I see to be exactly the image the laser scans,
    so that the walls I look at are the walls my car hits.
## Implementation Decisions

### Crash fault attribution (`collision`)

- **`collide()` returns the penalized vehicles, not all contactors.** The engine
  calls `.crash()` on everything it returns, so the return contract is the whole
  seam. Wall hits are always returned. For a racing pair within the collision
  distance, the fault rule picks which vehicle(s) are returned.
- **Per-pair instigator from closing velocity.** For a pair A, B the closing
  speed of each toward the other is the component of that vehicle's velocity
  vector on the unit vector from the other to it. The vehicle with the larger
  closing speed is the sole instigator. This makes rear-enders (follower at
  fault), side swipes (crossing car at fault), and T-bones (the car moving into
  the other at fault).
- **Mutual fallback.** If the two closing speeds are within a small tie window,
  or both negligible (head-on cancellation or a stationary overlap), both
  vehicles are penalized — matching today's behavior.
- **One crash per tick.** A vehicle already returned by the wall pass or by an
  earlier pair drops out of later pairs, so at most one crash registers per
  tick even in a pile.
- **Wall-first, self-fault.** A vehicle whose footprint is in a wall is always a
  wall crash and is dropped out of the pair pass. If a wall-hitter is also the
  pair instigator, the wall crash alone stands (it is returned once, from the
  wall pass).
- **Piles compose pairwise.** In a multi-vehicle pile, a car at fault in even
  one pair is the instigator and is returned once; a car that is only ever the
  victim in every pair it touches is returned by no pair and kept racing.

### Innocent vehicle untouched

- The innocent vehicle is not in `collide()`'s return, so the engine never calls
  `.crash()` on it — its `crashes` counter, `last_crash`, status, and pose are
  all unchanged for the tick.
- The instigator goes through the existing `crash()` path unchanged: pre-reset
  position recorded on `last_crash`, motion zeroed, crash registered (pause or
  DNF), reset to the nearest centerline pose, and it is then immune on the next
  tick via the existing pause→ghost→racing sequence. No new invulnerability
  rules are introduced.

### Map layer

- **`map_display_image()` serves the base image, not the `-gimp` variant.** The
  static message's `map_image` block and the `/map-image` route resolve to the
  same base image the scan grid and occupancy checks are built from. The
  `-gimp` preference is removed; the base image is the only shipped answer.
- On the default `icra-2023-short` the base and `-gimp` are pixel-identical, so
  this is a no-op there; on `right-interior` (52,994 differing pixels) and
  `icra-2025` (5,903) the picture now matches the physics.

### Frontend (client-side only)

- **Solid trail.** The trail for each vehicle is drawn as one continuous path
  (`moveTo` once, then `lineTo` down the recorded poses) so adjacent segments
  join instead of each getting its own round-capped, fade-stepped stroke. The
  body is drawn at full alpha in the vehicle's color.
- **Tail fade preserved.** The trailing end still fades: the path is drawn in
  dist-banded alpha so the last portion dims toward the window cut like today,
  but the body is one clean stroke.
- **Crash Xs at 2× size.** The X radius doubles from its current value.
- **Crash X colors.** Each X is stroked in the crashing vehicle's identity color
  (`colorFor(v)`), not the fixed red, so the marker names whose crash it was.
- **Last crash only.** The per-vehicle mark list is capped to the single most
  recent crash; older marks are dropped as new ones arrive, so the map shows
  the latest crash point for each car. Both wall and vehicle-to-vehicle crashes
  push a mark (the engine already ships a v2v instigator's `last_crash`).
- **No protocol change.** The dynamic message already carries `last_crash` for
  every vehicle each tick; the static message already carries the map-image
  placement. Color remains client-owned (existing identity palette).

## Testing Decisions

- Tests assert external behavior — serialized messages, returned vehicle lists,
  rendered-HTML references, engine-visible state — never rendering internals.

- **Collision seam** (`tests/test_collision.py`, priority). Extends the
  existing targeted `collide` tests to the new return contract: a rear-end
  returns only the follower; a side swipe returns only the crosser; a head-on
  returns both; a wall hit beats being a pair instigator in the same tick; a
  pile penalizes each instigator once and keeps an only-victim racing; the
  mutual/tie fallback still returns both. Prior art: the existing
  `test_racing_pair_below_distance...` and `test_wall_hits...` tests.
- **Engine seam** (`tests/test_engine.py`): a scripted v2v crash asserts the
  instigator's `last_crash` is set and it takes a pause, while the innocent
  keeps racing with an unchanged `crashes` count, status, and pose across the
  tick. Prior art: the existing crash-and-reset engine tests.
- **Map seam** (`tests/test_web_protocol.py`): `map_display_image` for a map
  track resolves to the base image path rather than the `-gimp` variant; the
  static message's map block still carries placement. Prior art: the existing
  `test_static_message_carries_the_map_image_block`.
- **Frontend structural seam** (`tests/test_web_frontend.py`, existing pattern,
  no browser): the page's `drawCrashMarks` references `colorFor`, holds the
  doubled size and last-crash-only cap; the trail draws one continuous path
  with fade. Prior art: `test_index_html_colors_every_vehicle_status`.
- No slow-tier work expected: changes touch collision attribution, a
  serialization preference, and the page. Fast suite covers it.

## Out of Scope

- Ray-cast or exact surface-contact refinement of where a crash X lands; the
  pre-reset pose remains the shipped answer.
- Simulating the collision impulse or diverting the innocent's motion; the
  innocent's trajectory is not altered by being hit.
- Per-vehicle fault history or a replay of all crashes; only the single most
  recent crash X is shown per vehicle.
- Changing the crash pause/ghost/DNF limits, lap counts, or the collision
  distance itself.
- Server-assigned colors or any color protocol field; color stays client-side.
- Rethinking the `-gimp` variant or migrating the scan grid to it; the base
  image is authoritative for the sim and is now the display.
- HUD changes or console/headless rendering of any of the above.

## Further Notes

- The crash-rule change makes a behavior change in the *result* of a race:
  side-swipe and rear-end collisions no longer cost the victim a crash. The race
  rules (`CONTEXT.md` "Crash" entry) and README's crash section should be
  updated in lockstep.
- The `looks-and-feel` spec previously committed to serving the `-gimp` display
  image; this spec reverses that so view and simulation share one source of
  truth. The default track's base and `-gimp` images are identical, so the
  reversal is visibly a change only on `right-interior` and `icra-2025`.
- Trail and X changes are purely the client page; nothing in the engine or
  protocol needs to know about color or mark sizing.