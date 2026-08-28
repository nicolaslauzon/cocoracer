# 09: Live start queue

**What to build:** in live (web) mode, the engine is constructed without auto-start so the field waits. The WebSocket handler accepts client messages of type `start` and pushes them to a thread-safe queue; the sim loop drains the queue every tick and calls `start()` itself, so exactly one thread mutates the engine. The first start message wins; later ones are ignored.

**Blocked by:** 08 (engine waiting phase).

**Status:** ready-for-agent

- [ ] A live run begins in phase `waiting` with the sim clock frozen
- [ ] A `start` message over the WebSocket releases the field on the next tick
- [ ] The engine is mutated only by the sim thread (the web thread only enqueues)
- [ ] The first start message wins; duplicate start messages are ignored
- [ ] Headless runs start immediately with no button, unchanged
