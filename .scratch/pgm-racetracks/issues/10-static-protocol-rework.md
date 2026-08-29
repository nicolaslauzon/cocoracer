# 10: Static protocol rework

**What to build:** the static connect message carries the track name, centerline, the two wall curves, track length, vehicle dimensions (length, width), and the start line. The occupied-cell list and the constant track width are dropped — the connect payload goes from megabytes (Spa shipped ~1.6 million coordinate pairs) to tens of kilobytes, and the view can draw the exact road. Wall curves are sent downsampled to ~1 m spacing for the payload; in-process curves stay at full resolution. The dynamic message is unchanged except that `phase` can now be `waiting`.

**Blocked by:** 03 (wall-curve track model).

**Status:** ready-for-agent

- [x] The static message contains the wall curves, track length, vehicle dimensions, and start line
- [x] The static message no longer contains the occupied-cell list or a constant width
- [x] Wall curves in the payload are downsampled to ~1 m spacing; the in-process track is unaffected
- [x] The dynamic message carries the `waiting` phase
- [x] The front-end structural test still asserts the page covers every protocol field, so a renamed key fails CI (the page is updated to the new field set in this ticket or the next; the suite is green when this lands)
