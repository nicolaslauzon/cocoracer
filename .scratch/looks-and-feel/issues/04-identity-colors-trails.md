# 04: Identity colors and 2 m trails

**What to build:** every vehicle gets its own bright color while racing, and the drawn path becomes a bold ribbon in that color. A fixed unordered palette of 8 bright colors (pink, blue, red, green, yellow, orange, purple, magenta-family) is assigned client-side by the vehicle's order in the messages; colors are deterministic per vehicle so page reloads keep the same colors, and fields larger than 8 get deterministic extras generated from the vehicle's identity, spread to avoid near-duplicates. Status colors: racing = the identity color, finished = white, DNF = black, paused and ghost = dimmed grey via the existing per-status alpha dimming. Trails are drawn at 2.0 m (world-scaled) in the vehicle's color; aging, fading, and the half-lap window are unchanged. No protocol change.

**Blocked by:** 03 (pixel-art sprite — both tickets live in the page's rendering; sequencing avoids conflicts).

**Status:** done

All five tickets merged to master. Commits: crash position `dc43b7e`, respawn cooldown `83651a5`, sprite `ebcd72b`, map layer `2670e9c`/`ffd6e34`, identity colors + trails `c8a61d4`. Fast suite 208 passing, mypy at the baseline 12 environment-stub errors only. HUD untouched; wall curves stay in the protocol but are no longer drawn.

- [x] Each racing vehicle renders in its own bright palette color, stable across page reloads
- [x] Fields larger than 8 vehicles still give every car a distinct, deterministic color
- [x] Finished = white, DNF = black, paused/ghost = dimmed grey; cars and trails follow the same mapping
- [x] Trails are drawn at 2.0 m in the vehicle's color, with aging and fading unchanged
- [x] Frontend structural test: the page references the fields it colors on
- [x] All four checks green