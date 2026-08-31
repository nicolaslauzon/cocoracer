# 01: Extract start-rotation into a track helper

**What to build:** the "rotate the centerline so the start line sits at the middle of the longest straight" logic lives in the track module as a reusable helper, not inside the F1 importer. The importer calls the helper and behaves exactly as before, so the new map import (ticket 06) and the eventual F1 removal (ticket 16) don't need to copy or lose the logic.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Rotation logic callable from the track module on any closed centerline
- [x] F1 importer delegates to the helper; all existing importer tests pass unchanged, including the committed-file match test
- [x] All four checks (ruff format, ruff check, mypy, pytest) green
