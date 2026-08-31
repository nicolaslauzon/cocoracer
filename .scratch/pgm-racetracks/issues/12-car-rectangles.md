# 12: True-scale car rectangles

**What to build:** each car renders as a true-scale rectangle built from the vehicle dimensions in the static message: a status-colored body, two black wheel bars across the front and rear axles, and a grey front window. The body keeps the current status colors (racing, paused, ghost, finished, DNF) so vehicle state is readable at a glance, and each car has a minimum visible pixel size. Heading and size read like a top-down car.

**Blocked by:** 10 (static protocol rework, for the vehicle dimensions).

**Status:** done

- [x] The car body is a rectangle at the true vehicle length × width, rotated by heading
- [x] Two black wheel bars sit across the front and rear axles; a grey front window is present
- [x] Body color still maps one-to-one to vehicle status (racing, paused, ghost, finished, DNF)
- [x] Each part has a minimum visible pixel size so the car never vanishes at distance
