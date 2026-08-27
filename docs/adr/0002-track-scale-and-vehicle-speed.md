# Run imported tracks at 1:12 scale with a faster vehicle

Full-scale F1 circuits are kilometres long: at 1:1, Spa's wall grid at 0.1 m
resolution would be ~270M cells (144× the area) and a 10 m/s vehicle would crawl
across multi-hundred-metre straights. We import at 1:12 (scale 1/12) and raise
the vehicle's limits — max speed 10→25 m/s, max accel 3→8 m/s², steer rate
3→4 rad/s — so the shrunk corner radii stay drivable and the straights are used
rather than coasted.

At 1:12 the tightest corner (Spa, ~0.96 m) clears the vehicle's geometric
minimum turning radius (wheelbase / tan(max_steer) ≈ 0.60 m) with margin, and
the largest grid (Spa, 1738×1082 at 0.1 m) is ~1.9M cells — no memory or
per-tick cost change that would force a substep collision model.

## Considered options

- **Full scale (1:1)**: faithful to the real circuits, but the wall grids and
  per-tick ray cost blow up and the vehicle is far too slow to feel like racing.
- **1:12 + faster vehicle** (chosen): keeps every wall grid under ~2M cells,
  keeps every corner drivable, and lets the vehicle actually use the straights.
- **1:12 + original vehicle**: corners are drivable but the straights become dead
  space; the vehicle spends most of the lap near its old top speed.

## Consequences

- The 0.25 m centerline spacing, 1.0 m track width, and 0.1 m grid resolution
  are matched to the 1:12 scale; changing the scale requires re-deriving them and
  re-tuning the vehicle and baselines together.
- Baseline gains were scaled up to match the faster vehicle (e.g. target speed
  4→15 m/s).
