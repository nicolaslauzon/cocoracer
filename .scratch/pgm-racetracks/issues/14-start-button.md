# 14: Start button

**What to build:** the web view has a Start button, visible exactly while the phase is `waiting`, that sends the start message. The player can load the page, study the track with the field held and the sim clock frozen, and choose when the countdown releases the field.

**Blocked by:** 09 (live start queue), 10 (static protocol rework, for the `waiting` phase in the dynamic message).

**Status:** ready-for-agent

- [x] The Start button is visible exactly while the phase is `waiting`
- [x] Pressing it sends the start message, which releases the field and begins the countdown
- [x] The button is gone once the countdown starts
- [x] The front-end structural test asserts the button element and the start-message type
