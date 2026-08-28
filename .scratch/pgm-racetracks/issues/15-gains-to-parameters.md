# 15: Gains to parameters rename

**What to build:** the word "gains" is replaced by "parameters" in the baseline controllers and their tests, so code vocabulary matches what the param file actually holds. The `_GAINS` tuple becomes `_PARAMETERS` in all three baselines, the `gains` locals become `parameters`, docstrings change from "Every gain comes from the param file" to "Every parameter comes from the param file", and the missing-key test is renamed to match. Out of scope: the starter's `CENTER_GAIN` (a genuine control-theory gain constant), the `kp`/`kd` key names, and the historical files under the old feature's scratch directory.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] `_GAINS` is `_PARAMETERS` in all three baselines and the `gains` locals are `parameters`
- [ ] Docstrings read "Every parameter comes from the param file"
- [ ] The missing-key test carries the renamed name
- [ ] The starter's `CENTER_GAIN`, the `kp`/`kd` keys, and the old scratch directory are untouched
- [ ] Controller contract tests pass unchanged
