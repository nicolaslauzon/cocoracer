# 17: Player onboarding

**What to build:** A newcomer goes from clone to first race with zero outside help. A README quickstart: install, copy the controller stub into the controllers folder, implement the tick function, run a time trial, run a head2head against a baseline, open the web view. The stub documents the tick contract (state fields, the 360° laser scan and `np.inf` no-hit, the speed/steering outputs, internal state between ticks, allowed imports) and points at the vehicle control limits in the param file. CLI help is polished for both subcommands (including the headless flag). Dependencies are tidy: everything used is listed, teleop/matplotlib deps are gone.

**Blocked by:** 13 (Web front end), 14 (Wall-follow baseline), 15 (Gap-follow baseline), 16 (Multi-vehicle traffic + tick budget)

**Status:** ready-for-agent

- [ ] README quickstart works end-to-end from a fresh clone: install → copy stub → run time trial → run head2head vs a baseline → watch the web view
- [ ] The stub documents the tick contract (state fields, laser scan, `np.inf` no-hit, outputs, internal state) and points at the vehicle limits in the param file
- [ ] CLI `--help` for both subcommands documents every option, including the headless flag
- [ ] Dependencies are tidy: all used deps listed, no teleop/matplotlib deps remain
- [ ] README documents all modes (time trial, head2head, N-vehicle), the three baselines, the crash → pause → ghost rules, and how to add a new track
