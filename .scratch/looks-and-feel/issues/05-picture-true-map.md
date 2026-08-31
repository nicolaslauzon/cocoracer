# 05: Picture-true map layer

**What to build:** the web view shows the shipped display PGM image itself instead of a synthetic re-drawing. The server serves each map's `-gimp` variant (white road, grey background, wall outlines as drawn in the picture) and the static message gains a map-image block: the image URL plus its placement — resolution, origin, and pixel dimensions from the map's existing metadata. The client draws the image in world coordinates with its existing view transform and stops drawing the synthetic road fill and the left/right wall-curve overlays entirely; the wall curves remain protocol fields but are never rendered. Physics stay on the occupancy grid, which is already derived from the same picture.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The server serves the display PGM for the selected map
- [ ] The static message carries the map-image block (URL, resolution, origin, pixel dimensions)
- [ ] The client renders the image in world coordinates; the road fill and wall-curve overlay drawing are gone
- [ ] Static-message tests cover the map-image block for each shipped map
- [ ] Frontend structural test: the page references the map-image fields and no longer references the wall-curve fields for drawing
- [ ] All four checks green