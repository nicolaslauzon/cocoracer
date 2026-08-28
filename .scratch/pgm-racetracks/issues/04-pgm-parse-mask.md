# 04: PGM P5 parse and drivable mask

**What to build:** a P5 PGM image parses at track construction into a drivable mask: a pixel at or above the threshold is drivable, everything else is wall. The threshold defaults to 250 (the maps' drivable pixels are 254, background 205, outlines 0) and can be overridden per track. Only the largest drivable connected component is kept — the maps carry 1–6 px anti-aliasing specks that are dropped, not errored on.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] P5 parse produces a boolean drivable mask at the image's dimensions
- [ ] Threshold default 250, overridable per track; a synthetic PGM in a temp dir verifies the override
- [ ] Anti-aliasing specks are dropped: only the largest connected component survives
- [ ] All three shipped maps parse to a single component of the expected size
