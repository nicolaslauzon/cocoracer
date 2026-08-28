# 05: Map topology: hole check and boundary matching

**What to build:** from a cleaned drivable mask, the track build finds the interior hole and the two wall boundaries. The mask must enclose exactly one interior hole — zero holes or more than one is a track error. The outer boundary and the hole boundary are matched by polar angle around the hole centroid; each boundary must be star-shaped about that centroid (a single radius per angle) or the build fails. The output is two ordered, closed boundary curves.

**Blocked by:** 04 (PGM parse and drivable mask).

**Status:** ready-for-agent

- [ ] A single closed ring with one hole yields two ordered, closed boundary curves
- [ ] Zero holes is a track error with a clear message
- [ ] More than one hole is a track error with a clear message
- [ ] A non-star-shaped boundary (synthetic PGM in a temp dir) is a track error
- [ ] No bad file silently produces a weird track: every failure mode raises at build time
