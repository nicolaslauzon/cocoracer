# Track geometry sources

`f1-circuits-geodata.geojson` is a vendored copy of the F1 circuit
centerline collection from <https://github.com/scluba/f1-circuit-geodata>.

- Commit: `a05d7ee59c5b41bf4094c977f298f72958fbee2a` (2025-07-26)
- Collection license: MIT (see the upstream repo)
- The underlying geometries were traced from OpenStreetMap data, which is
  licensed ODbL; OSM contributors retain copyright of their mappings.
- Fetched: 2026-08-27. SHA-256:
  `121fbf3df263c5f0bc7839ac02a27bbc4eea3f3334e5c90b6fc040b7066492ca`

Circuits used (feature `id` in the GeoJSON, all `variant: current`):

| id        | circuit                     | track file name  |
| --------- | --------------------------- | ---------------- |
| cn-gv-02  | Circuit Gilles Villeneuve   | `montreal`       |
| bl-sf-07  | Circuit de Spa-Francorchamps| `spa`            |
| br-ss-11  | Silverstone Circuit         | `silverstone`    |

Only factual circuit names are used; no Formula 1 branding, logos, or
licensed assets are included anywhere in this repo.

To regenerate the track files after a change to this file or to the import
pipeline: `python -m cocoracer.trackimport`.
