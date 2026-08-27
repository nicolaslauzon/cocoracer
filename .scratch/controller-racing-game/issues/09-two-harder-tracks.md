# 09: Two harder tracks

**What to build:** Two additional closed-loop tracks, ascending in difficulty beyond the stadium (chicanes and radius variation), authored through the track builder, closure-validated, selectable via the CLI track argument, and playable by the shipped baselines. They render correctly in the web view from the static track message.

**Blocked by:** 04 (Race mode + pure-pursuit reference)

**Status:** ready-for-agent

- [ ] Both new tracks build and pass closure validation; each is selectable via the CLI track argument
- [ ] Pure pursuit completes N laps on each new track (headless runs)
- [ ] Wall follow and gap follow run end-to-end on the new tracks (completing or DNFing is acceptable; crashing the game is not)
- [ ] Both tracks render correctly in the web view from the static message
