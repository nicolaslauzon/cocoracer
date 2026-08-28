# 17: Player onboarding

**What to build:** A newcomer goes from clone to first race with zero outside help. A README quickstart: install, copy the controller stub into the controllers folder, implement the tick function, run a time trial, run a head2head against a baseline, open the web view. The stub documents the tick contract (state fields, the 360° laser scan and `np.inf` no-hit, the speed/steering outputs, internal state between ticks, allowed imports) and points at the vehicle control limits in the param file. CLI help is polished for both subcommands (including the headless flag). Dependencies are tidy: everything used is listed, teleop/matplotlib deps are gone.

**Blocked by:** 13 (Web front end), 14 (Wall-follow baseline), 15 (Gap-follow baseline), 16 (Multi-vehicle traffic + tick budget)

**Status:** ready-for-agent

- [x] README quickstart works end-to-end from a fresh clone: install → copy stub → run time trial → run head2head vs a baseline → watch the web view
- [x] The stub documents the tick contract (state fields, laser scan, `np.inf` no-hit, outputs, internal state) and points at the vehicle limits in the param file
- [x] CLI `--help` for both subcommands documents every option, including the headless flag
- [x] Dependencies are tidy: all used deps listed, no teleop/matplotlib deps remain
- [x] README documents all modes (time trial, head2head, N-vehicle), the three baselines, the crash → pause → ghost rules, and how to add a new track

## Comments

Done in `wt-17` (2026-08-28). Added `README.md`: install → copy `controllers/starter.py` → time trial → head2head → web view, plus all modes (time trial, head2head, N-vehicle), the three baselines, the crash → pause → ghost rules, and add-a-track (inline `segments` or JSON `centerline`). Wrote the documented starter stub `controllers/starter.py` — full tick-contract docstring and a pointer at the `vehicle:` limits, plus a laser-only centering driver that finishes the stadium clean. Polished `cocoracer/cli.py` `--help` for both subcommands, including the `--no-web` headless flag. Verified deps are tidy (numpy, jax, scipy, pyyaml, fastapi, uvicorn, websockets; no teleop/matplotlib). Added `tests/test_starter.py`. Four checks green.
