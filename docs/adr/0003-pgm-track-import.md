# Build tracks from PGM map images at real scale (~0.6 m/px)

The vendored F1 circuit geodata (ADR-0001) and its 1:12 import scale
(ADR-0002) are gone: the three F1 tracks, the importer, and the geodata are
deleted, leaving one track source. The game's tracks are now built from the
three PGM map images that ship in the repo (`right-interior`,
`icra-2023-short`, `icra-2025`): white pixels are the drivable surface, every
other pixel is wall, and track width varies exactly as the map shows —
something the constant-width centerline model cannot express.

## Decision

- **PGM import at track construction.** Each map is a PGM image plus a
  per-map centerline CSV and a standard robot-world metadata YAML. The
  direction and the start/finish pixel are param-file keys; map starts are
  pixel-specified, not computed.
- **Scale ~0.6 m per pixel.** The PGM metadata's native resolution is
  0.05 m/px; the track build applies a 0.6 m/px scale, so the physics numbers
  (m, m/s, a ~90 km/h top end) are real-life in magnitude.
- **One-eighth vehicle.** With the ~0.6 m/px scale the car is ~2 m wide —
  about one eighth of the narrowest corridor — so the car reads as a car on
  the track rather than a truck (previously 40% of a 1.0 m road). There is
  one fixed vehicle for the whole game; no per-track variants.

## Consequences

- `cocoracer/pgm.py` and `cocoracer/maptrack.py` own the import; `Track`
  builds a variable-width wall pair and a double-upsampled occupancy grid
  from the mask.
- The stadium stays as a hand-authored segment track; hand-authored
  constant-width tracks remain possible through the segments and
  centerline-JSON paths.
- Baseline parameters are re-derived for the new car and track scale.
- Default track is `icra-2023-short`, the shortest lap to iterate on.
