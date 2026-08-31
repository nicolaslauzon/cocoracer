Status: done

# Spec: Looks & Feel — Crash Xs, Respawn Cooldown, Trails, Pixel-Art Cars, Picture-True Map

## Problem Statement

The web view no longer looks like the game the player is driving. Crash Xs land at the car's post-reset centerline position instead of where the wall was hit, so the evidence of a crash points at the wrong place. A crashed car is back in the race so fast the pause is barely visible. The drawn path is a thin thread that is hard to follow next to the road. Every car is colored by its status, so in a pack of racing cars all bodies look alike and there is no way to tell whose trail is whose. The cars are drawn as abstract rectangles. And the map layer is a synthetic re-drawing — a flat road fill plus stroked wall curves — that shows lines which do not exist in the map picture the physics actually comes from.

## Solution

The engine records the vehicle's pose at the crash tick (before the centerline reset) and ships it in the dynamic message; the client drops the X exactly there. The crash pause becomes a visible two-second stop, still tunable from the param file. The trail is drawn at the car's own width — a bold ribbon of the car's color. Every vehicle gets its own bright identity color while racing; the status colors remain for the other states. The cars are rendered from a single shipped pixel-art F1 sprite (black tires, two-color body) recolored per vehicle at load, so editing one image restyles the whole fleet. The map layer is the shipped display PGM image itself — what you see is the picture the scan and collisions are computed from — and the synthetic road fill and wall-curve overlays are gone. The HUD is untouched.

## User Stories

1. As a player, I want each crash X to land at the position where the vehicle actually crashed, so that the marks on the map tell me where the walls bite.
2. As a player, I want a crashed vehicle to stay stopped for two seconds before respawning, so that a crash is a visible event and I can read the situation.
3. As a player, I want the crash pause to be a param-file number, so that I can make respawns faster or slower without touching code.
4. As a player, I want the drawn vehicle path to be about as wide as the car, so that the racing line reads at a glance.
5. As a player, I want each vehicle to have its own bright color while racing, so that I can follow my car in a pack.
6. As a player, I want the trail to take the vehicle's identity color, so that path and car read as one.
7. As a player, I want finished cars to show white, DNF cars black, and paused or ghosting cars dimmed grey, so that the status of the field is still legible now that color means identity while racing.
8. As a player, I want the cars drawn as simple pixel-art F1 racers — black tires and a two-color body in the vehicle's color — so that the grid looks like a race, not a diagram.
9. As a player, I want the car sprite shipped as a single editable image, so that I can restyle the whole fleet by editing one file.
10. As a player, I want colors to be stable across page reloads, so that my pink car is still pink after I refresh.
11. As a player, I want a race with more than eight vehicles to still give every car a distinct color, so that big fields stay readable.
12. As a player, I want the map layer to be the shipped display image itself, so that what I see is exactly the picture I race on.
13. As a player, I want the synthetic wall-curve lines and flat road fill gone from the view, so that no lines appear that are not in the map picture.
14. As a player, I want the HUD left alone, so that the numbers I rely on do not move under me.

## Implementation Decisions

- **Crash position recording**: the engine, at the tick a crash is registered, records the vehicle's pre-reset pose — its (x, y) before the centerline resync — on the vehicle. No ray-cast contact refinement: the recorded point is where the car was when it crashed. This resolves the open question recorded during the pgm-racetracks effort.
- **Protocol**: the dynamic message's per-vehicle object gains `last_crash` — `{x, y}` or `null` before the first crash. The client keeps its existing crash-mark aging (marks live for half a lap of driving); it just anchors each new mark at `last_crash` instead of the reported post-reset position.
- **Respawn cooldown**: `crash_pause` moves from 0.5 s to 2.0 s in the param file and the config default. No rule change — crash → paused (motion zeroed) → ghost as today; only the pause duration moves.
- **Trail width**: the client draws trails at 2.0 m (world-scaled, as today's 0.2 m is). Aging, fading, and the half-lap window are unchanged.
- **Identity colors**: client-side only, no protocol change. A fixed unordered palette of 8 bright colors (pink, blue, red, green, yellow, orange, purple, magenta-family) is assigned by the vehicle's order in the messages (fleet/grid order). Colors are derived deterministically per vehicle — not per page load — so reloads keep the same colors. For fields larger than 8, colors beyond the palette are generated deterministically from the vehicle's identity (name-based hash), spread to avoid near-duplicates.
- **Status colors**: racing = the vehicle's identity color, finished = white, DNF = black, paused and ghost = dimmed grey through the existing per-status alpha dimming. Cars and trails both follow this mapping.
- **Car sprite**: one PNG asset ships with the web package — a simple top-view pixel-art F1 car: black tires, body in a single key color, darker shade of the same color for cockpit and wing details. No grey window. At load the page builds one recolored copy per vehicle by replacing the key-colored body pixels with the vehicle's color, leaving tires and shading intact. The sprite is drawn rotated by yaw and scaled to the vehicle's world dimensions (the existing length/width from the static message).
- **Map layer**: the server serves each map's display PGM (the `-gimp` variant: white road, grey background, wall outlines as drawn in the picture). The static message gains a map-image block: the image URL plus its placement — the YAML `resolution` and `origin` and the pixel dimensions — so the client can draw the image in world coordinates with its existing view transform. The client stops drawing the synthetic road fill and the left/right wall-curve overlays entirely; the wall curves remain in the protocol (structural tests reference them) but are never rendered.
- **Scan display**: the per-vehicle scan continues to be sent and continues to be unused by the page.
- **HUD**: untouched.

## Testing Decisions

- Tests assert external behavior — serialized messages, rendered HTML references, engine-visible state — never drawing internals or CSS.
- **Engine/protocol seam** (the highest existing seam): a scripted-crash engine test asserts the dynamic message's `last_crash` equals the vehicle's pre-reset pose and that it is `null` before any crash. Prior art: the dynamic-message shape and scan-serialization tests in the web-protocol test module.
- **Config seam**: the crash-pause default is 2.0 s and the param file round-trips it; the existing config tests cover the loading pattern.
- **Frontend structural seam** (existing pattern, no browser): the test extracts every field name the serializers emit and asserts the page references them, so the new `last_crash` and map-image fields fail CI if the page forgets them; it asserts the sprite asset exists and is referenced; it asserts the wall-curve overlay and road-fill drawing are gone (the page no longer references the wall-curve field names for drawing — they remain protocol fields). Prior art: the web-frontend test module.
- **Static message seam**: the map-image block carries the display PGM URL plus resolution/origin/dimensions for each shipped map. Prior art: the static-message test in the web-protocol test module.
- No slow-tier work is expected: nothing here touches dynamics, collision math, or baseline controllers beyond recording a pose. The fast suite covers it.

## Out of Scope

- Ray-cast contact-point refinement of the crash X; the pre-reset pose is the shipped answer.
- Any change to crash rules, ghost duration, DNF limits, lap counts, or timeouts beyond the pause duration.
- Per-vehicle colors assigned or stored server-side; no protocol field for color.
- Sprite sheets, multiple sprite variants, or per-vehicle sprite files.
- Rendering the laser scan, grid, centerline, or start-line geometry on the map.
- HUD redesign or any HUD field changes.
- Trail aging, window, or fade changes beyond width and color.
- Headless/console rendering of any of the above; the console output stays results-only.

## Further Notes

- Physics already run entirely on the occupancy grid derived from the clean PGM's drivable mask; the display PGM is the same picture with the wall outlines drawn in, so view and simulation now share one source of truth visually as they already do computationally.
- The `-gimp` YAMLs duplicate the clean YAMLs' `resolution` and `origin`; the server reads placement from the map's existing metadata rather than new per-map configuration.
- The palette is deliberately unordered and client-owned: it is presentation, not state, and a future multi-client or spectator story can lift it into the static message without rework of the engine.
- The trail at 2.0 m equals the vehicle width; on the narrowest corridors (~1.08 m on icra-2025) the ribbon will cover the road across its width — accepted by the player as the intended look.
