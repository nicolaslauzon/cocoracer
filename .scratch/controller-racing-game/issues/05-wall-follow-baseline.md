# 05: Wall-follow baseline

**What to build:** The wall-follow baseline, following F1TENTH Lab 3 semantics: scan a forward sector, hold a target lateral distance from the chosen wall via a P/D controller on the heading error to an offset target point, with speed = v_ref × (1 − k·|steering|) clamped. Every gain, offset, sector angle, and speed factor is a parameter in the param file under its own baseline block, so aggressiveness is tunable without code changes.

**Blocked by:** 04 (Race mode + pure-pursuit reference)

**Status:** ready-for-agent

- [ ] Wall follow completes N laps on the stadium track (headless run)
- [ ] All gains (target wall distance, P and D gains, v_ref, steering-speed factor, sector angles) are parameters in the param file and changing them changes behavior
- [ ] Speed scales down with steering angle (observable in run telemetry/results)
- [ ] Head2head wall follow vs pure pursuit runs end-to-end with a valid results table
