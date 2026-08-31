# 02: Two-second respawn cooldown

**What to build:** a crashed vehicle stays stopped for two seconds before respawning, as a param-file number the player can tune. `crash_pause` moves from 0.5 s to 2.0 s in the param file and the config default. No rule change: crash → paused (motion zeroed) → ghost exactly as today.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] `crash_pause` is 2.0 s in the param file and the config default
- [ ] Config test: the default loads as 2.0 and a param file can override it
- [ ] All four checks green