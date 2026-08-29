# 11: Road rendering

**What to build:** the web view draws the road as the region between the two wall curves at true variable width — narrow chicanes read as tight, wide straights as fast. A dashed centerline is drawn over the road, and the start line is drawn spanning between the two walls so it stays visible on a road whose width changes.

**Blocked by:** 10 (static protocol rework).

**Status:** ready-for-agent

- [x] The road is filled between the two wall curves, not a constant-width band
- [x] A dashed centerline is drawn over the road
- [x] The start line spans from wall to wall
- [x] The front-end structural test passes against the updated field set
