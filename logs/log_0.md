# RGMs migration log (log_0)

## Iteration — `spm_dir_norm` (Phase 0)

**Inspected:** `rgms-rules.mdc`, `AGENTS.md`, migration docs, `Python Matlab Translation Issues.md`; template Python modules and oracle tests under `python_src/` and `tests/oracle/`; `tests/conftest.py`, `tests/helpers/matlab_engine.py`, `tests/helpers/compare.py`.

**Copied:** `C:\Users\andre\Documents\MATLAB\spm12\spm_dir_norm.m` → `matlab_src\spm_dir_norm.m` (file was absent in `matlab_src`).

**Created:** `python_src\spm_dir_norm.py`, `tests\oracle\test_spm_dir_norm.py`.

**Modified:** `python_src\spm_dir_norm.py` (cell input handling: avoid NumPy stacking a list of same-shaped `ndarray` cells into a numeric tensor; use explicit `dtype=object` buffer and `np.errstate` around divide to mirror MATLAB `rdivide` before zero-column overwrite).

**Shared files touched:** none.

**Blockers / notes:** `conda` env `rgms` initially lacked `pytest`, `numpy`, and `scipy`; installed via `pip` into `rgms` so oracle tests could run. No changes to `matlab_compat.py` or `tests/helpers/`.

**Oracle:** `pytest tests\oracle\test_spm_dir_norm.py` — all tests passed.

---

**Note:** Created `notes\andrew Python Matlab Translation Issues.md` — branch-specific translation issues file: copies settled content from repo-root `Python Matlab Translation Issues.md` and adds a settled section on MATLAB cell semantics vs naïve `np.asarray` (from the `spm_dir_norm` iteration). Repo-root `Python Matlab Translation Issues.md` was not modified.

---

## Iteration — `spm_vec` (Phase 0, Tier 0 item 0.6)

**Inspected:** `rgms-rules.mdc`, `AGENTS.md`, `Migration Plan.md`, `Migration Tactics.md`, `notes\andrew Python Matlab Translation Issues.md`, this log; templates `python_src\spm_log.py`, `spm_cat.py`, `spm_sum.py`, `spm_dir_norm.py`, `spm_cross.py`, `spm_dot.py`; oracle tests `test_spm_log.py`, `test_spm_cat.py`, `test_spm_sum.py`, `test_spm_dir_norm.py`; `tests\conftest.py`, `tests\helpers\matlab_engine.py`, `tests\helpers\compare.py`; MATLAB source `C:\Users\andre\Documents\MATLAB\spm12\spm_vec.m` (and `spm_unvec.m` for staging only).

**Copied:** `spm_vec.m` and `spm_unvec.m` from read-only SPM into `matlab_src\` (both were absent; no overwrites).

**Created:** `python_src\spm_vec.py`, `tests\oracle\test_spm_vec.py`.

**Modified:** `logs\log_0.md` (this entry).

**Shared files touched:** none (`matlab_compat.py` and `tests\helpers\` unchanged).

**Temporary / debug files:** none created or deleted.

**Oracle:** `conda activate rgms` then `python -m pytest tests\oracle\test_spm_vec.py` — 9 passed. No conda packages installed or environment mutation for this iteration.

**Not done this pass:** `spm_unvec` (Python and oracle) — awaiting explicit transition after review.

---

## Iteration — `spm_unvec` (Phase 0, Tier 0 item 0.7)

**Inspected:** `rgms-rules.mdc`, `AGENTS.md`, `Migration Plan.md`, `Migration Tactics.md`, `notes\andrew Python Matlab Translation Issues.md`, this log; `matlab_src\spm_unvec.m`, `python_src\spm_vec.py`, `spm_dir_norm.py`, `spm_cat.py`; `tests\oracle\test_spm_vec.py`, `test_spm_dir_norm.py`, `test_spm_cat.py` (partial); `tests\conftest.py`, `tests\helpers\matlab_engine.py`, `tests\helpers\compare.py`; `matlab_src\spm_length.m` (reference only for private `_spm_length` mirroring).

**Copied:** none (`matlab_src\spm_unvec.m` already present from prior SPM copy).

**Created:** `python_src\spm_unvec.py`, `tests\oracle\test_spm_unvec.py`.

**Modified:** `logs\log_0.md` (this entry).

**Shared files touched:** none (`matlab_compat.py` used only via existing `as_matlab_array` import; `tests\helpers\` unchanged).

**Temporary / debug files:** none created or deleted.

**Implementation notes:** `spm_unvec.py` includes a file-local `_spm_length` matching `spm_length.m` (not yet ported as its own module), duplicates `_cell_as_object_array` / `_iscell` patterns aligned with `spm_vec` and Andrew-branch cell rules; leaf templates use `as_matlab_array` for raw 1-D numeric/logical so row-vector orientation matches MATLAB `(1,n)` unvec output.

**Oracle:** `conda activate rgms` then `python -m pytest tests\oracle\test_spm_unvec.py` — 10 passed. No conda or tooling changes.

---

## Iteration — evaluation: canonical vs `misc\depr` (`spm_dir_norm`, `spm_vec`, `spm_unvec`)

**Inspected (read-only where noted):** `matlab_src\spm_dir_norm.m`, `spm_vec.m`, `spm_unvec.m`; canonical `python_src\spm_dir_norm.py`, `spm_vec.py`, `spm_unvec.py`; `tests\oracle\test_spm_dir_norm.py`, `test_spm_vec.py`, `test_spm_unvec.py`; alternative `misc\depr\spm_dir_norm.py`, `spm_vec.py`, `spm_unvec.py` and paired `misc\depr\test_*.py`; `matlab_compat.py` (for `as_matlab_array` / `full` coherence).

**Executed:** `git branch --show-current` (on `andrew`); `conda activate rgms`; `python -m pytest tests\oracle\test_spm_dir_norm.py tests\oracle\test_spm_vec.py tests\oracle\test_spm_unvec.py` — **11 passed**; ad-hoc `importlib` load of `misc\depr` modules vs canonical on tensor `spm_dir_norm` fixture (depr produced **NaNs**, canonical matched oracle tensor numerics).

**Created / deleted:** briefly created `misc\_tmp_matlab_tensor_check.py` during a quoting experiment, **deleted immediately** (misc remains effectively untouched for policy).

**Modified:** `logs\log_0.md` (this entry only).

**Shared files touched:** no.

**Findings (summary):** canonical tree is wired to repo policy (`python_src` + `tests\oracle`, MATLAB Engine oracles, `matlab_compat` + `spm_length` usage on `spm_unvec`). `misc\depr` implementations diverge on **Dirichlet tensor** normalization (`spm_dir_norm`) relative to canonical/MATLAB-oracle behavior; `misc\depr\test_*.py` still **`from python_src...` import** — they validate **canonical** code, not the `misc\depr` modules, so the “alternative tests” are misaligned as committed. Recommendation recorded for stakeholders: **keep canonical** as repo truth; treat `misc\depr` as exploratory only unless tests are rewired and tensor semantics fixed.

**Follow-up — `misc\depr` test harness + dual runs:** `pytest` does not load `tests\conftest.py` for paths under `misc\depr\` (not a descendant of `tests\`), so `eng` was unavailable until either a temporary repo-root `conftest.py` (used during evaluation, then removed) or the permanent fix documented in the next iteration. With MATLAB Engine available: **`misc\depr` test files × canonical `python_src` imports** → **19 passed, 5 failed** (failures confined to `test_spm_unvec.py`: sparse template expected a SciPy sparse return with `.toarray()` but canonical returned a dense `ndarray`; nested round-trips compared MATLAB **0-D scalar** shapes to Python **`(1, 1)`** fields). **Same `misc\depr` tests × `misc\depr` implementations** (loaded via a short-lived `_tmp_misc_depr_tests_impl_swap.py` that replaced `sys.modules['python_src.spm_*']` before `pytest.main`, file deleted after) → **24 passed**. Interpretation: the expanded `misc\depr` suite exercises **vec/unvec** edges (sparse output, scalar nesting) where the alternative `spm_unvec` matches those expectations and MATLAB in those scenarios, but that suite **does not include** the canonical **`spm_dir_norm` tensor** oracle; canonical remains necessary for full MATLAB alignment on Dirichlet tensors.

---

## Iteration — `misc\depr\conftest.py` (MATLAB Engine fixture for deprecated-side oracle tests)

**Created:** `misc\depr\conftest.py` — re-exports session `eng` from `tests.helpers.matlab_engine` (same surface as `tests\conftest.py`) so `pytest misc\depr\test_*.py` discovers the MATLAB Engine fixture without placing `conftest.py` at repo root.

**Modified:** `logs\log_0.md` (this entry and small clarification in the evaluation paragraph above).

**Shared files touched:** no.

**Check:** `python -m pytest misc\depr\test_spm_unvec.py::test_spm_unvec_matrix_standalone_oracle` — passed under `conda activate rgms`.

---

## Iteration — alternative `spm_unvec` / `spm_vec` wiring (`misc\depr`)

**Created:** `misc\__init__.py`, `misc\depr\__init__.py` (empty package markers so `misc.depr.spm_vec` imports resolve from repo root).

**Modified:** `misc\depr\spm_unvec.py` (`from misc.depr.spm_vec import spm_vec`); `misc\depr\test_spm_unvec.py` (imports `spm_unvec` and `spm_vec` from `misc.depr`); `misc\depr\phase0_three_functions_differences_eval.md` (test-suite and `spm_unvec` sections updated for the new wiring and current pytest behavior).

**Oracle:** `conda activate rgms` then `python -m pytest tests\oracle\test_spm_unvec.py misc\depr\test_spm_unvec.py` — **14 passed** (four canonical oracle + ten `misc\depr` alternative-stack).

**Shared files touched:** no.

---

## Iteration — `misc\depr` tests import only `misc.depr` (dir_norm + vec)

**Modified:** `misc\depr\test_spm_dir_norm.py`, `misc\depr\test_spm_vec.py` (`from misc.depr.spm_*`); `misc\depr\phase0_three_functions_differences_eval.md` (test wiring and reproducibility); `logs\log_0.md` (this entry).

**Oracle:** `python -m pytest tests\oracle\test_spm_dir_norm.py tests\oracle\test_spm_vec.py tests\oracle\test_spm_unvec.py misc\depr\test_spm_dir_norm.py misc\depr\test_spm_vec.py misc\depr\test_spm_unvec.py` — **35 passed** (11 canonical + 24 `misc\depr` on alternative stack).

**Shared files touched:** no.

---

## Iteration — off-diagonal cross tests + eval docs (`misc\depr`)

**Created:** `misc\depr\test_cross_oracle_on_alternative_spm_dir_norm.py`, `test_cross_oracle_on_alternative_spm_vec.py`, `test_cross_oracle_on_alternative_spm_unvec.py`, `test_cross_misc_depr_on_canonical_spm_dir_norm.py`, `test_cross_misc_depr_on_canonical_spm_vec.py`, `test_cross_misc_depr_on_canonical_spm_unvec.py` (duplicate bodies of `tests\oracle` vs `misc\depr` scenarios with swapped `python_src` / `misc.depr` imports only; **no edits** to original `tests\oracle\` or primary `misc\depr\test_spm_*.py`).

**Modified:** `misc\depr\phase0_three_functions_differences_eval.md` (full cross-matrix section, reproducibility), `misc\depr\phase0_three_functions_differences_eval_CHAT_19apr2026.md` (prepended current-matrix summary + pointer to eval doc), `logs\log_0.md` (this entry).

**Oracle:** `python -m pytest` on the six `test_cross_*` files — **28 passed, 7 failed** (tensor `spm_dir_norm` + struct-heavy `spm_vec` on alternative; five canonical `spm_unvec` expanded cases as documented).

**Shared files touched:** no.

---

## Iteration — single eval doc (`misc\depr`)

**Deleted:** `misc\depr\phase0_three_functions_differences_eval.md`, `misc\depr\phase0_three_functions_differences_eval_CHAT_19apr2026.md`.

**Created:** `misc\depr\spm_phase0_canonical_vs_alternative_evaluation.md` — consolidated evaluation (implementations, import boundaries, diagonal + cross tests, recorded **63 passed / 7 failed** on full primary+cross aggregate, per-failure analysis, merge guidance, reproducibility).

**Modified:** `logs\log_0.md` (this entry).

**Shared files touched:** no.

---

## Iteration — team evaluation note (`misc\depr\phase0_three_functions_differences_eval.md`)

**Created:** `misc\depr\phase0_three_functions_differences_eval.md` — prose evaluation of canonical `python_src` versus alternative `misc\depr` implementations for `spm_dir_norm`, `spm_vec`, and `spm_unvec`, including test-suite overlap, tensor `spm_dir_norm` semantics, sparse and scalar-shape behavior on `spm_unvec`, import wiring, and reproducibility pointers.

**Modified:** `logs\log_0.md` (this entry).

**Shared files touched:** no.

---

## Iteration — compact `spm_phase0_canonical_vs_alternative_evaluation.md`

**Modified:** `misc\depr\spm_phase0_canonical_vs_alternative_evaluation.md` (single intro + two sentences on cross tests + one `##` section per function).

**Modified:** `logs\log_0.md` (this entry).

**Shared files touched:** no.
