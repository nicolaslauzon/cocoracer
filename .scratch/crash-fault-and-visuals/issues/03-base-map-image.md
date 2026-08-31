# 03: Serve the base map image the laser scans

**What to build:** the live view shows exactly the picture the car races on.
The map layer the player sees is the base map image the laser scan and
collision grid are computed from, not the decorative `-gimp` variant whose wall
outlines disagree with the physics on some tracks. On the default track the two
images are pixel-identical, so this is a no-op there; on the maps where they
differ, what you see now matches what the car hits.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] The map image served to the live view is the base image, not the `-gimp`
      variant.
- [x] The static map placement block and the map-image route resolve to that same
      base image, with placement unchanged.
- [x] On the default track the visible rendering is unchanged (base and `-gimp`
      are identical there).