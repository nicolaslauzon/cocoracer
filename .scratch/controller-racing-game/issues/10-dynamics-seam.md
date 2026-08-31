# 10: Dynamics seam

**What to build:** The dynamics interface becomes `step(states (N, 5), commands (N, 2)) -> (N, 5)`: pose/speed/steering plus targets in, stepped pose out. `pack_state` is deleted from dynamics; the column order is documented exactly once, in the module docstring; the (N, 7) array packing stays private to the jitted kernel; `DynamicsParams.as_array` and `warmup(n)` are unchanged. The engine builds the two arrays itself. Race results are numerically unchanged by the refactor.

**Blocked by:** 05 (Ghost driving — behaviour change) — sequencing, both touch the engine tick

**Status:** done

- [x] `Dynamics.step` takes (N, 5) states plus (N, 2) commands and returns (N, 5); `pack_state` is gone; the (N, 7) packing is private to the kernel
- [x] The column order appears in exactly one place (the dynamics docstring); `mypy` is clean
- [x] The recorded `RaceResult` fingerprint (StadiumDriver, default config) is captured before the change and still holds after it
- [x] All four checks green: `ruff format .`, `ruff check .`, `mypy cocoracer tests`, `pytest`

## Comments

- 2026-08-27: Done. `Dynamics.step(states (N, 5), commands (N, 2)) -> (N, 5)`; the
  jitted kernel concatenates both into the (N, 7) array internally (same column
  order as before, so bit-identical math) and returns only the stepped pose.
  `pack_state` deleted; the engine's `_integrate` builds the two arrays itself.
  Column order documented only in the dynamics module docstring — the private
  `X, Y, ... = range(7)` index constants remain as kernel indices, not docs.
  Fingerprint (StadiumDriver 2.0, default config, 3 laps): captured to
  /tmp/opencode/fingerprint-before.txt before the change, re-captured after,
  diff is empty — bit-identical, no JAX nondeterminism. Deliberate deviation:
  no fingerprint test added to tests/test_engine.py; the existing
  `test_race_is_deterministic` covers self-relative determinism, and pinning
  full-precision floats would go stale on JAX/BLAS updates. All four checks
  green (90 tests).
