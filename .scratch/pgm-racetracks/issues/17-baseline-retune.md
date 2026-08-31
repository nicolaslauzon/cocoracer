# 17: Baseline re-tune

**What to build:** every baseline parameter block and the starter are re-derived from their old values by the scale factor, then adjusted headless until each baseline and the starter drives more than half a lap on every map track. All baseline numbers stay in the param file so the player can fine-tune without touching code. This is the bar for having working opponents to beat from the first run; the fine tuning beyond it is the player's.

**Blocked by:** 16 (F1 removal, so the default and the track set are final).

**Status:** done

- [x] ~~Each of the three baselines and the starter drives more than half a lap on every map track, verified headless~~ — requirement dropped by the player (2026-08-31): the baselines will be fine-tuned by hand, no half-lap bar applies
- [x] ~~All baseline numbers remain in the param file (no tuning constants in code)~~ — unchanged by the scope cut; numbers were already param-file only
- [x] ~~A one-shot verification script runs each controller on each map track and asserts maximum progress along the centerline exceeds half the track length (not part of CI)~~ — dropped with the half-lap bar
- [x] ~~CI keeps a short headless smoke per map track plus the existing tick-budget performance test~~ — the fast suite already covers track building and engine seams per map; no change made

## Comments

- 2026-08-31: Closed without implementation — the player decided to tune the baselines personally, so the half-lap acceptance bar and the verification script are no longer wanted. Ticket 16 (the blocker) is merged to master.
