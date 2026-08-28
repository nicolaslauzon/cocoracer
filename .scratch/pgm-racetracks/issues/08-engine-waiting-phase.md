# 08: Engine waiting phase

**What to build:** the engine has a new initial phase `waiting`, entered when the engine is constructed without auto-start. While waiting, a tick is a no-op: the sim clock stays frozen at 0.0 and vehicle state is unchanged. `start()` releases the field: the countdown begins in race mode, and time-trial mode releases immediately. The headless entry point auto-starts, so its contract is unchanged.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] An engine constructed without auto-start is in phase `waiting`
- [x] Ticks while waiting advance nothing: time frozen at 0.0, vehicle state unchanged
- [x] `start()` begins the countdown in race mode and releases immediately in time-trial mode
- [x] The auto-start path behaves exactly as before; all existing engine tests pass
