# 05: Centerline file: parse, scale, and wall derivation

**What to build:** the track builder reads a map's centerline file and its metadata and produces the track's centerline and two wall curves. The centerline CSV holds one row per point: `x, y, w_right, w_left` in the map's native meters (the PGM metadata frame); the metadata YAML holds `resolution` (0.05 m/px) and `origin` (corner, y-up). Points and distances are converted to track world (origin at the image corner, y-up) by subtracting the origin and multiplying by track scale / image resolution (0.6 / 0.05 = 12× by default; the scale is the track's, overridable). The converted points are resampled and splined by the existing Frenet machinery to become the centerline; the two wall curves are the pointwise offsets of the resampled centerline by `w_left` / `w_right` along its local normals. Consistency with the map image: sampled wall points must sit within a small tolerance of the drivable mask's boundary, and the corridor between the walls must be drivable per the mask (largest connected component, ticket 04); a violation is a track error with a clear message. A malformed CSV (wrong column count, non-numeric values) is a track error.

**Notes:** when measuring the corridor against the mask, walk outward along the wall normal, not along image rows — these maps meander, so a row-walk follows the road instead of crossing it. Expect the mask corridor to run a few percent wider than the CSV's `w_left + w_right` (the walls sit a hair inside the drivable edge); the tolerance must absorb that.

**Blocked by:** 03 (wall-curve track model), 04 (PGM parse and drivable mask).

**Status:** ready-for-agent

- [ ] CSV + YAML parse: native meters converted to track world (corner origin, y-up, × scale/resolution)
- [ ] Wall curves are pointwise normal offsets of the resampled centerline; median wall-to-wall distance ≈ scaled `w_left + w_right`
- [ ] Sampled wall points sit on the mask boundary within tolerance and the corridor is drivable per the mask; a mismatched synthetic map (temp dir) is a track error
- [ ] A malformed CSV is a track error with a clear message
- [ ] All three shipped maps' centerlines derive walls that pass the mask consistency check
- [ ] The four checks are green
