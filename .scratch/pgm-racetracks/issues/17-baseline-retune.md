# 17: Baseline re-tune

**What to build:** every baseline parameter block and the starter are re-derived from their old values by the scale factor, then adjusted headless until each baseline and the starter drives more than half a lap on every map track. All baseline numbers stay in the param file so the player can fine-tune without touching code. This is the bar for having working opponents to beat from the first run; the fine tuning beyond it is the player's.

**Blocked by:** 16 (F1 removal, so the default and the track set are final).

**Status:** ready-for-agent

- [ ] Each of the three baselines and the starter drives more than half a lap on every map track, verified headless
- [ ] All baseline numbers remain in the param file (no tuning constants in code)
- [ ] A one-shot verification script runs each controller on each map track and asserts maximum progress along the centerline exceeds half the track length (not part of CI)
- [ ] CI keeps a short headless smoke per map track plus the existing tick-budget performance test
