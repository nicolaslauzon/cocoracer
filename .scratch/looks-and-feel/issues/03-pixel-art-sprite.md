# 03: Pixel-art F1 sprite

**What to build:** the cars are drawn as simple top-view pixel-art F1 racers from a single shipped PNG asset — black tires, body in one key color, darker shade of the same color for cockpit and wing details, no grey window. At load the page builds one recolored copy per vehicle by replacing the key-colored body pixels with the vehicle's color, leaving tires and shading intact, and draws the sprite rotated by yaw and scaled to the vehicle's world dimensions. Editing the one PNG restyles the whole fleet.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] One PNG asset ships with the web package; the page loads and references it
- [ ] Each vehicle renders as the sprite recolored to its color, tires/outline intact, rotated by yaw, scaled to the vehicle's length and width
- [ ] The rectangle body and grey window drawing are gone
- [ ] Frontend structural test: the asset exists and the page references it
- [ ] All four checks green