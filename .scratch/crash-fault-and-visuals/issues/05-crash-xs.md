# 05: Crash Xs — 2× size, in car color, last-crash only, shown for v2v too

**What to build:** crash evidence is readable and correct. Each crash X is twice
as big as today, drawn in the crashing vehicle's own identity color so you can
see whose crash it was, and each vehicle keeps only its single most-recent
crash X so the map does not fill with old scars. Xs appear for both wall crashes
and vehicle-to-vehicle crashes.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Crash X marks render at 2× their current size.
- [x] Each X is stroked in the crashing vehicle's identity color (not a fixed
      red), staying consistent with the vehicle's color while racing.
- [x] A crash X is drawn for a vehicle-to-vehicle crash, not just a wall crash.
- [x] Each vehicle shows only its single most-recent crash X; older marks are
      dropped as new ones arrive.