# Import real F1 circuit geodata instead of authoring tracks procedurally

The original plan (issue 09) was to hand-author harder closed-loop tracks as
segment specs (straights and turns) through the track builder. We instead vendor
OSM-derived F1 circuit centerlines (`scluba/f1-circuit-geodata`, MIT collection,
ODbL underlying data) and import them as closed-loop tracks. Real circuits are
immediately drivable and plausible, their corner radii are known and can be
checked against the vehicle's limit at authoring time, and they cost no
per-track authoring effort.

## Considered options

- **Hand-authored segment specs** (original plan): full control, but every track
  is bespoke work, "harder" is subjective, and there is no guarantee the
  resulting radii are drivable.
- **Hand-digitized polylines**: more realistic shape than segments, but still
  manual, error-prone, and unattributed.
- **Vendored F1 geodata** (chosen): real, attributable, drivable, and zero
  authoring. Cost: a vendored data file plus an import pipeline to own, and a
  scale to pick (see ADR-0002).

## Consequences

- `cocoracer/trackimport.py` is an offline authoring tool (run with
  `python -m cocoracer.trackimport`), not a runtime track editor — the spec's
  "no track editor" still holds; the import emits param files.
- `TrackSpec` accepts either a `segments` list or a `centerline` polyline,
  mutually exclusive. The stadium stays segment-based; the three F1 tracks are
  centerline-based.
- `params/tracks/*.json` are generated artifacts; regenerate them rather than
  editing by hand.
