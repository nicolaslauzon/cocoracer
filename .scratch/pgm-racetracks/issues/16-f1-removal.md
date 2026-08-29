# 16: F1 removal, default flip, and ADR

**What to build:** the F1 geodata pipeline is gone, leaving one track source. Deleted: the track importer module and its tests, the vendored F1 geodata and its source note, the three F1 per-track JSON files, their param-file entries, and the F1 test fixture. The default track flips to `icra-2023-short` (the shortest lap to iterate on), and the CLI and README examples switch to the new track names. A new ADR records the PGM import, the ~0.6 m/px scale, and the one-eighth vehicle rule; ADRs 0001 and 0002 get superseded-by headers pointing at it rather than being deleted, so the history of the 1:12 decision stays readable.

**Blocked by:** 01 (extract start-rotation, so the importer's deletion loses nothing), 07 (ship the three maps, so the default flip lands on working tracks).

**Status:** ready-for-agent

- [ ] The importer module, its tests, the vendored geodata and source note, the three F1 JSONs, their param entries, and the F1 fixture are deleted
- [ ] `rotate_to_straightest_start` and `_segment_turns` in the track module are deleted with their tests (the F1 importer was their only user; map starts are pixel-specified)
- [ ] No reference to F1 or the geodata remains in the codebase
- [ ] The default track is `icra-2023-short`; CLI and README examples use the new track names
- [ ] A new ADR records the PGM import, the ~0.6 m/px scale, and the one-eighth vehicle rule
- [ ] ADRs 0001 and 0002 carry superseded-by headers pointing at the new ADR and are not deleted
- [ ] All four checks green
