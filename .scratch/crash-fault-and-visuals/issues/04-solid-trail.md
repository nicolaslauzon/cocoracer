# 04: Draw the trail as one solid line, tail fade kept

**What to build:** the colored path behind a vehicle reads as a continuous
solid ribbon, not a string of circles at the recorded poses. The per-vehicle
trail is drawn as one continuous path in the vehicle's color so adjacent
segments join cleanly, while the trailing end still fades out toward the
window cut so the trail stays legible on a long track.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Each vehicle's trail renders as one continuous line (a single open path)
      in its identity color, with no visible breaks between recorded poses.
- [ ] The tail still fades into the distance toward the trail window, so the
      whole trail does not render at uniform opacity.
- [ ] The trail keeps its color mapping for every status (racing color, dimmed
      ghost/paused, white/black finished/DNF).