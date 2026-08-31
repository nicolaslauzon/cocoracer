# 13: Trails and crash Xs

**What to build:** each car leaves a client-side trail of its last half lap of driven path, faded by age, with an X dropped at every crash location. The trail accumulates the car's positions from the dynamic messages, keeps the last half lap of driven arc length, and breaks at a crash (no straight line drawn from the crash point to the centerline reset). Both the trail and the Xs age out after half a lap of driving, so stale history stops cluttering the view. This is purely a front-end concern: no trail state on the server and no trail fields in the protocol.

**Blocked by:** 10 (static protocol rework, for the world scale).

**Status:** done

- [x] Each car's trail accumulates from the dynamic messages and keeps the last half lap of driven arc length
- [x] The trail is faded by age
- [x] A crash drops an X at the crash point and breaks the trail (no line to the centerline reset)
- [x] The trail and the Xs expire on the same half-lap arc-length window
- [x] No trail state on the server and no trail fields in the protocol
