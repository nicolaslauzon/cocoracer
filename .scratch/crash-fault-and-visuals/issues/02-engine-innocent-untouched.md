# 02: Wire attribution into the race engine (innocent untouched)

**What to build:** the race loop crashes exactly the vehicles the detector
penalizes, so a vehicle-to-vehicle crash lands only on the instigator. On a
collision, the instigator records its pre-reset crash position, takes the pause
(or crash-DNF), and survives the next tick via the existing pause→ghost→racing
immunity; the innocent car is completely untouched — unchanged crash counter,
identity status, pose, and no result change — and simply keeps racing. The
one-crash-per-tick and pile behavior hold at the engine boundary.

**Blocked by:** 01 (Instigator-only fault attribution).

**Status:** ready-for-agent

- [ ] On a v2v crash the instigator's pre-reset crash position is recorded and it
      takes the pause, then ghost→racing immunity.
- [ ] The innocent car's crash count, status, and pose are provably unchanged
      across the crash tick; it keeps racing.
- [ ] A v2v crash does not push the innocent toward its DNF crash limit.
- [ ] One crash per tick holds for the instigator even in a multi-vehicle pile.