# 06: Gap-follow baseline

**What to build:** The gap-follow baseline, following F1TENTH Lecture 5 semantics: over a forward cone (±60°), find the widest gap between opposing wall hits in the laser scan, steer toward the gap midpoint at a fixed lookahead, with speed = min(v_max, k_gap × gap_width) × (1 − k·|steering|). Every gain, cone angle, lookahead, and speed factor is a parameter in the param file under its own baseline block.

**Blocked by:** 04 (Race mode + pure-pursuit reference)

**Status:** ready-for-agent

- [ ] Gap follow completes N laps on the stadium track (headless run)
- [ ] All gains (cone angles, lookahead, k_gap, steering-speed factor) are parameters in the param file
- [ ] Speed is limited by gap width and scales down with steering angle
- [ ] Head2head gap follow vs pure pursuit runs end-to-end with a valid results table
