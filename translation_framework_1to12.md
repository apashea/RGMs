# Translation framework: Entries 1–12 (`DEM_AtariIII.m`)

**Repository:** `C:\Users\andre\.cursor\RGMs\`  
**Authoritative ledgers:** `Atari_example.md` (ordered entries), `12DEF.md` (Entry 12 bands 12D–12F), `Migration Plan.md` (global port order)  
**Branch policy:** `andrew` (see `rules/rgms-rules.mdc`)  
**Last status refresh:** 2026-05-21 — Entry **12** Phase **1** sign-off per `matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt` (Validation **12** exit **0** on `rgms_canonical`)

---

## 1. Overarching goal

Translate the non-visual **`DEM_AtariIII.m`** pipeline into faithful Python so that:

1. **Entries 1–11** reproduce the staged Atari ledger through **`RDP.T = 64`** (`spm_set_goals` → `spm_set_costs` → `spm_mdp2rdp`).
2. **Entry 12** runs **`PDP = spm_MDP_VB_XXX(RDP)`** with variational BP parity on the **FSL oracle `RDP`** lane.
3. Eventually, **`run_dem_atariiii`** in `DEM_AtariIII.py` calls translated code end-to-end **without** Entry-12-only compare scaffolding (Phase **2**).

MATLAB under `C:\Users\andre\Documents\MATLAB\spm-main\` is **read-only** truth; staged mirrors live in `matlab_src\`; Python in `python_src\`.

---

## 2. Operating model (two execution modes)

| Mode | Purpose | When used |
|------|---------|-----------|
| **Python-native** | Target runtime semantics | Default development; measures real translation progress |
| **MATLAB-testing** | Temporary MATLAB substitutions at known bottlenecks | Preserves downstream oracle continuity while upstream numeric gaps remain (Entry **4** MI/eig/link; optional Entry **8**/**9** captures) |

Do not retire a substitution until boundary evidence supports it for all downstream consumers.

---

## 3. Verification architecture

### 3.1 Entries 1–11 — per-entry + FSL gate

| Layer | What it proves | Primary artifacts |
|-------|----------------|-----------------|
| **Per-entry oracle tests** | Each `%%% ENTRY n` boundary in isolation or smoke | `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry*.py`, `test_spm_*.py` |
| **FSL 1–11 driver** | Full Python ledger run through Entry **11** | `test_DEM_AtariIII_full_staged_atari_ledger_1_11.py` → `fixtures/DEMAtariIII_fsl_1_11_ctx.pkl` |
| **Validation 1–11** | Python `ctx["RDP"]` vs MATLAB nested `RDP` | `fsl_1_11_compare_ctx_pkl_to_mat.py` → `matlab_custom/fsl_1_11_compare_ctx_pkl_to_mat_output.txt` |

**ENTRY 1–11 policy note:** Provisional acceptance of **`511` vs `485`** hidden-state extent drift on FSL `RDP` (likelihood `A`, transition `B`, `H`) — upstream ledger sizing, not Entry **12** VB bugs. Authority: tagged lines in Validation **1–11** tee.

### 3.2 Entry 12 — four-script oracle (Phase 1)

| Script | Role | Key outputs |
|--------|------|-------------|
| **1a** | `entry12_preflight_vb_rand_k.py` — preflight draw count `K` | `fixtures/entry12_vb_rand_K.mat` |
| **1b** | `DEMAtariIII_entry12_dump_all_subentries.m` — MATLAB truth + `vb_rand_buf` | `fixtures/DEMAtariIII_entry12_<tag>_12{A–I}.mat`, `DEMAtariIII_entry12_vb_matlab_rand_buf.mat`, `DEMAtariIII_XXX_12_rdp.mat` |
| **3** | `test_DEM_AtariIII_XXX_12.py` — Python VB with **`reuse_matlab_draws=True`** | `fixtures/DEMAtariIII_entry12_<tag>_12*.pkl`, `DEMAtariIII_XXX_12_pdp.pkl` |
| **4** | `XXX_12_compare_pdp_pkl_to_mat.py` — Validation **12** | Overwrites `matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt` |

**Phase 1 done when:** script **4** exit **0** on gating bands (**12A–12C**, **12D–12F** causal + value paths, **12H**, **12I**, input **`RDP`**, final **`PDP`**; **12G** excluded — `OPTIONS.B=0` on Atari).

**Three pillars (Entry 12):**

- **A — Scripts only** for sign-off (no ad-hoc VB runners).
- **B — RNG** — replay `vb_rand_buf`; `entry12_draw_index_audit.py` → `unused_draws=0`.
- **C — Causal order** — **12D → 12E → 12F** per `t`; fix first red.

### 3.3 Class A / B / C discrepancy taxonomy

| Class | Meaning | Typical location |
|-------|---------|------------------|
| **A — Compute** | Python VB/ledger semantics differ from MATLAB | `spm_MDP_VB_XXX.py`, `DEM_AtariIII.py`, structure-learning kernels |
| **B — Compare / load / cast** | Artifacts differ in nesting, index order, or representation; values match after honest align | `entry12_matlab_capture.py`, `entry12_loadmat_convert.py`, `XXX_12_compare_pdp_pkl_to_mat.py` |
| **C — Type-walk volume** | Representation-only noise (e.g. `(1,1)` float vs int scalar); may not fail value assert | Reported in tee; lower priority than **A** once value assert passes |

---

## 4. Current project status (summary)

### 4.1 Entries 1–11

| Entry | Snippet role | Python-native | Oracle / notes |
|-------|--------------|---------------|----------------|
| **1** | `rng` + reproducibility | Translated | `test_spm_MDP_generate` chain |
| **2** | `spm_MDP_pong` | Translated | Oracle closed |
| **3** | `spm_MDP_generate` | Translated | Oracle closed |
| **4** | `spm_faster_structure_learning` | Translated; **active bottlenecks** | MI scalar envelope ~1e-15 candidate; **spectral order/chosen unresolved**; link `spm_dir_MI` scoped 1e-15 policy |
| **5** | forget `a`/`b` | Translated | Oracle closed |
| **6** | hits/miss windows | Translated | Oracle closed |
| **7** | `spm_merge_structure_learning` | Isolated oracle **closed**; **in-context lane not closed** (Entry **4** lineage) | MATLAB-testing hooks available |
| **8** | training-window merges | Entry **8** replay oracle **closed** on capture; full `outer=128` capture build heavy | Artifact-first |
| **9** | `spm_RDP_basin` + counters | Deep oracle **closed** at documented ladder; `xfail` on path-string parity | Artifact-first |
| **10** | `spm_RDP_sort`, goals, `P` | **Closed** on capture | |
| **11** | `spm_set_goals/costs`, `spm_mdp2rdp`, `RDP.T=64` | Translated; oracle on capture | |
| **ENTRY 1–11 gate** | Full staged ledger | Python FSL run + Validation **1–11** | **511 vs 485** provisionally accepted on FSL compare |

### 4.2 Entry 12 (Phase 1)

| Milestone | Status (`rgms_canonical`, 2026-05-21) |
|-----------|----------------------------------------|
| Causal **12D→12E→12F** (15 steps) | **OK** |
| **12A, 12B, 12C, 12H, 12I** value assert | **OK** |
| Final **PDP** value assert | **OK** |
| **Validation 12** full script | **exit 0** |
| **12G** | Postponed (non-gating; `spm_backwards` not on Atari path) |

**Phase 2 (not started):** `ctx["RDP"]` → nested dict matching FSL **structure/types** for product `run_dem_atariiii(entry_stop=12)` without resizing **511→485**.

---

## 5. Core patterns in the final code

### 5.1 Compute lane (`spm_MDP_VB_XXX.py` and satellites)

These are **class A** behaviors required for faithful VB; several were proven via causal **12D–12F**, others via **12H** / full **PDP**.

1. **`spm_dot(B, [P])` bracket form** — When state and path dimensions coincide, list-wrapped `P` contracts the path axis like MATLAB (~2332+).

2. **Assemble before export (`_vb_assemble_mdp_results_1691`)** — Build `bundle.S` / `bundle.X` from per-`t` `P`/`Q` columns, then assign `md["P"]` / `md["X"]` (~4600–4616). Matches MATLAB ~1663–1673.

3. **Hierarchical `Q.O` append** — Flat `shiftdim` row indexing `t + g*ncol`; variable `No(g)` row heights; matrix concat for `[Q.O{L} mdp.O]` (~1238), not naive Python list cat.

4. **`Q.s` / `Q.u` trajectory storage** — `_vb_hierarchical_q_append_level` uses **`np.hstack([old_m, new_m])`** for matrix `[old new]` (~1233–1234 MATLAB), not list-of-block concatenation (12H fix).

5. **Extracted VB helpers** (ported for XXX, used inside loop): `spm_forwards.py`, `spm_backwards.py`, `spm_VBX.py`, `spm_induction.py`, plus DEM support (`spm_parents.py`, `spm_MDP_checkX.py`, …).

6. **Stochastic replay** — `_vb_load_matlab_rand_buf` / `reuse_matlab_draws` in script **3**; not a substitute for standalone product RNG until Phase **2**.

7. **Workspace vs struct `A`** — Active learning updates **`bundle["A"]`**, not saved `MDP.A` on dumps; causal gates use **`A_peaks_*`** from `entry12_phase_log`, not full tensor compare on **12F** parent `MDP.A`.

### 5.2 Compare lane (`entry12_matlab_capture.py` + script **4**)

These are **class B** (mostly). They make paired `.mat` / `.pkl` **comparable** without changing VB compute.

1. **Layered PDP align (`entry12_align_mdp_to_mat_workspace`)**  
   - `_entry12_align_pdp_assemble_shell` — top-level `B`, `O`/`Y`/…, `Pa`, `id`, top-level `Q`.  
   - `_entry12_align_Q_record_to_mat` on inner `MDP.Q` when hierarchical (`L` in mat).  
   - `_entry12_strip_pdp_inspection_probes` — drop Python-only probes.  
   - Early return **without** `_spm_MDP_checkX_transform_align` on assembled **12H** (`MDP.G` layout mismatch).

2. **Order discipline for `mdp.Q`** — `_entry12_align_mdp_Q_for_12h` must **skip** `O,P,X,Y,j,i,o`; generic list align **before** `_entry12_align_Q_record_to_mat` corrupts `Q.O`.

3. **`_entry12_Q_O_level_to_mat_cells`** — One workhorse: dense Python matrix ↔ flat MATLAB post-`shiftdim` cell row (`t+g*ncol`).

4. **`_entry12_align_mdp_O_ng_t_cells`** — Assembled `MDP.O`: Python `O[t][g]` → MATLAB `O{g,t}` cell rows.

5. **Mat-side witness prep** — `entry12_mat_pdp_for_value_assert` / `entry12_mat_mdp_for_subentry_value_assert`: drop `G`, `Q.E`, probes; recursive `G` drop on **12A** nested `MDP`.

6. **Causal payloads** — Lean strips (`entry12_causal_payload_12d/e/f`, `_ENTRY12_CAUSAL_*_DROP`); **15** steps; first-red fix order.

7. **12F-specific** — `_entry12_align_12F_Rvw_at_t` (prefix `v`/`w`/`R`); nested policy trace strip on mat.

8. **12C-specific** — `_entry12_align_12c_O_preloop` (`None` → `[]`).

9. **`entry12_loadmat_convert.mat_nested_to_py`** — `.mat` nesting fidelity (`Y` as `[g][t]`, scalar cells as `int`, etc.).

10. **`Entry12CompareLaneError`** — Fail loud on impossible layout masking (honest compare).

### 5.3 Shared compare primitive

- **`tests/oracle/toolbox/DEM/test_spm_mdp2rdp.py`** — `_assert_nested_rdp_equal` (atol 1e-10; sparse class parity). Used by Validation **1–11** and **12**.

### 5.4 Entry 12 RNG contract

- Single **`vb_rand_buf`** replayed in MATLAB dump fork and Python XXX **12**.
- **`entry12_draw_index_audit.py`** — `K`, `unused_draws=0`, `sample_calls_match`.
- **Forbidden for sign-off:** Python re-seed, draw skipping, MAP-for-sample, mixed `tag` fixtures.

---

## 6. Remaining discrepancies vs full `DEM_AtariIII` translation

This section lists **known gaps** between “Phase 1 Entry 12 oracle green” and “product Python runs like MATLAB without Entry-12 scaffolding.”

### 6.1 Upstream ledger (Entries 1–11)

| Issue | Severity | Notes |
|-------|----------|-------|
| **FSL `511` vs `485` dim drift** | Accepted for ENTRY 1–11 | Python `ctx["RDP"]` vs `DEMAtariIII_fsl_1_11_rdp.mat`; do not force MATLAB extents in Phase **2** converter |
| **Entry 4 — `spm_MDP_MI` native byte parity** | Open (policy pending) | Scalar envelope ~1e-15 on replayed workload; not full byte-exact |
| **Entry 4 — spectral `order/chosen` in `spm_rgm_group`** | Open | Discrete mismatch; `RGMS_FSL_RGM_MATLAB_EIG=1` testing hook |
| **Entry 4 — link `spm_dir_MI`** | Scoped tolerance | `abs ≤ 1e-15` on `ss.ID`/`ss.IE` only |
| **Entry 7 in-context lane** | Open | Isolated merge closed; failures attributed to Entry **4** `idA`/`G` lineage in lane tests |
| **Entry 8 full `outer=128` capture** | Operational | Multi-hour MATLAB capture; Entry **8** replay oracle closed on existing artifacts |
| **Entry 9 path-string `xfail`** | Deferred | Extra `{1}` in Python path strings vs MATLAB; numeric contract OK on deep oracle |
| **Entry 7 tensor shape `(1,1,1)` vs `(1,1)`** | Deferred | Separate from path-string issue |
| **Phase 2 — no `ctx`→`RDP` converter** | Planned | `run_dem_atariiii(entry_stop=12)` smoke ≠ oracle lane |

### 6.2 Entry 12 — still compare-only or fork-dependent

| Issue | Class | Notes |
|-------|-------|-------|
| **12C pre-loop `O` shells** | B | Python `None` vs MATLAB `[]`; align at compare, not necessarily in `spm_MDP_VB_XXX` init |
| **12H/PDP type-walk noise** | C | e.g. `MDP.B[f]` ndarray vs int, `PDP.T` float vs int, `csr_matrix` vs `csc_array` — value assert passes with coerce + cast |
| **`MDP.G` / `Q.E` dropped on compare** | B witness | Documented in `Atari_example.md` final-stage review; not proven as compute-equivalent |
| **Top-level `PDP.O` truncated 64→20** | B | Atari-visible modalities vs full NG in Python dump |
| **`entry12_matlab_capture` required for sign-off** | Process | Not imported by production `DEM_AtariIII` |
| **MATLAB dump fork** | Process | `spm_MDP_VB_XXX_entry12_dump.m` is authoritative for `.mat`; Python `_vb_dump_save` mirrors but does not replace **1b** |
| **`spm_MDP_checkX` validation lane** | B exception | `transform=True` / `entry12_rdp_for_validation_from_mat_nested` — Entry **12** only |
| **12G / `spm_backwards`** | Out of scope | `OPTIONS.B=0` on Atari; code may exist, not gating |
| **VB monitor / segment timing** | Debug | `RGMS_ATARI_RUN_SEGMENT_TIMING=1`; not sign-off |
| **511 vs 485 on XXX 12 input** | Policy | Oracle **RDP** uses FSL **`.mat`** lane; ctx PKL (`RGMS_XXX_12_RDP_FROM_CTX=1`) is smoke only |
| **Ad-hoc `matlab_custom/_diag_*`** | Forbidden for sign-off | Debugging only per `Atari_example.md` |
| **Fold compare patterns into `spm_MDP_VB_XXX`** | Future | Final-stage checklist: audit before declaring “translation complete” without Entry-12 files |

### 6.3 Compute items to audit post–Phase 1

| Item | Status |
|------|--------|
| Empty `O` at 12C in compute vs compare-only | Open product decision |
| Whether `MDP.G` assemble should match MATLAB without dropping | Open |
| Full hierarchical `Q` record shape at save time without flatten helpers | Open |
| Product RNG without `vb_rand_buf` replay | Phase **2** / later |
| **`spm_backwards`** when `OPTIONS.B=1`** | Not Atari Phase 1 |

### 6.4 Environment and repo boundaries

| Item | Notes |
|------|-------|
| **Conda env `rgms`** | Required for all Python oracle runs |
| **`matlab_compat.py`** | Narrow shared mechanical helpers only |
| **`tests/helpers/`** | Minimal MATLAB Engine helpers — avoid expanding for Entry-12-specific logic |
| **External SPM tree** | Read-only; edits only in `matlab_src\` / `matlab_custom\` |
| **`misc\`** | User-only; agents do not read/write |

---

## 7. Snippet-to-entry map (fenced `DEM_AtariIII` ledger)

| Fence label | MATLAB essence | Primary Python surface |
|-------------|----------------|------------------------|
| ENTRY 1 | `rng`, game dims | `DEM_AtariIII.py`, `spm_MDP_generate` |
| ENTRY 2 | `spm_MDP_pong` | `spm_MDP_pong.py` |
| ENTRY 3 | `spm_MDP_generate` | `spm_MDP_generate.py` |
| ENTRY 4 | `spm_faster_structure_learning` | `spm_faster_structure_learning.py`, `spm_rgm_group.py`, `spm_MDP_MI.py`, `spm_dir_MI.py` |
| ENTRY 5 | forget parameters | `DEM_AtariIII.py` |
| ENTRY 6 | hits/miss / windows | `DEM_AtariIII.py` |
| ENTRY 7 | `spm_merge_structure_learning` | `spm_merge_structure_learning.py` |
| ENTRY 8 | training merges | `DEM_AtariIII.py` |
| ENTRY 9 | `spm_RDP_basin` | `spm_RDP_basin.py`, `spm_RDP_compress.py`, `spm_set_goals.py` |
| ENTRY 10 | sort, goals, `P` | `spm_RDP_sort.py`, `DEM_AtariIII.py` |
| ENTRY 11 | `spm_mdp2rdp`, `RDP.T=64` | `spm_set_costs.py`, `spm_mdp2rdp.py`, `spm_mdp2rdp_a.py` |
| ENTRY 12 | `spm_MDP_VB_XXX` | `spm_MDP_VB_XXX.py` (+ compare/capture stack below) |

---

## 8. How to re-verify (quick reference)

**Entry 12 Phase 1 sign-off:**

```powershell
cd C:\Users\andre\.cursor\RGMs
conda activate rgms
$env:PYTHONPATH = 'C:\Users\andre\.cursor\RGMs'
$env:RGMS_ATARI_RUN_XXX_12 = '1'
pytest tests/oracle/toolbox/DEM/test_DEM_AtariIII_XXX_12.py -q
python tests/oracle/toolbox/DEM/XXX_12_compare_pdp_pkl_to_mat.py --coerce-sparse-to-dense-for-compare
```

**Pass/fail tee:** `matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt` (causal block first, then subentries, then final PDP).

**FSL 1–11:** See `Atari_example.md` § **ENTRY 1-11** tables A–C.

---

## 9. Related policy documents

| Document | Role |
|----------|------|
| `Atari_example.md` | Ordered entries 1–12, acceptance policies, rerun blocks |
| `12DEF.md` | Living 12D–12F subgoal / witness discipline |
| `12DEF-archive.md` | Historical deep log (audit only) |
| `Migration Plan.md` | Global SPM port phases beyond Atari |
| `Migration Tactics.md` | Two-pass transliteration policy |
| `Python Matlab Translation Issues.md` | Settled corner cases |
| `notes/andrew Python Matlab Translation Issues.md` | Branch-specific corner cases |
| `AGENTS.md` | One-file oracle workflow |
| `rules/rgms-rules.mdc` | Workspace rules including Entry **12** framework |
| `rules/entry12-atari-framework.mdc` | Entry **12** trigger summary |

---

# Appendix A — Files associated with Entries 1–11

Paths are relative to repo root `C:\Users\andre\.cursor\RGMs\` unless noted. Lists are **project-associated** (implementation, tests, captures, fixtures, staged MATLAB). Generated checkpoints under `_checkpoint_data/` follow documented naming patterns; individual pickle files may be local-only.

## A.1 Policy and ledger

- `Atari_example.md` — § Entry **1** … § Entry **11**, § **ENTRY 1-11**
- `Migration Plan.md`
- `Migration Tactics.md`
- `AGENTS.md`
- `Python Matlab Translation Issues.md`
- `notes/andrew Python Matlab Translation Issues.md`
- `notes/andrew agent-user communication directives.md`
- `notes/structure_learning_plan_week2_22APR2026.md` (historical planning)
- `rules/rgms-rules.mdc`

## A.2 Shared runtime and helpers

- `matlab_compat.py` — cross-file mechanical MATLAB compat (narrow)
- `python_src/spm_cat.py`
- `python_src/spm_dot.py`
- `python_src/spm_cross.py`
- `python_src/spm_softmax.py`
- `python_src/spm_log.py`
- `python_src/spm_psi.py`
- `python_src/spm_dir_norm.py`
- `python_src/spm_vec.py`
- `python_src/spm_unvec.py`
- `python_src/spm_sum.py`
- `python_src/spm_zeros.py`
- `python_src/spm_betaln.py`
- `python_src/spm_cov2corr.py`
- `python_src/spm_KL_dir.py`
- `python_src/spm_length.py`
- `python_src/spm_check_version.py`
- `python_src/spm_combinations.py`
- `python_src/spm_kron.py`
- `python_src/spm_speye.py`
- `python_src/spm_Gcdf.py`
- `python_src/spm_MDP_MI.py` — Entry **4** grouping MI
- `python_src/spm_dir_MI.py` — Entry **4** link scalars
- `tests/helpers/__init__.py`
- `tests/helpers/matlab_engine.py`
- `tests/helpers/compare.py`

## A.3 Python implementation — `DEM_AtariIII` driver (Entries 1–11)

- `python_src/toolbox/DEM/DEM_AtariIII.py` — `run_dem_atariiii`, ledger entries **1–11** (and Entry **12** hook / smoke)

## A.4 Python implementation — per-entry toolbox (DEM)

- `python_src/toolbox/DEM/spm_MDP_pong.py` — Entry **2**
- `python_src/toolbox/DEM/spm_MDP_generate.py` — Entries **1**, **3**
- `python_src/toolbox/DEM/spm_faster_structure_learning.py` — Entry **4**
- `python_src/toolbox/DEM/spm_rgm_group.py` — Entry **4** (spectral grouping)
- `python_src/toolbox/DEM/spm_merge_structure_learning.py` — Entry **7**
- `python_src/toolbox/DEM/spm_RDP_basin.py` — Entry **9**
- `python_src/toolbox/DEM/spm_RDP_compress.py` — Entry **9** (support)
- `python_src/toolbox/DEM/spm_set_goals.py` — Entries **9**, **10**, **11**
- `python_src/toolbox/DEM/spm_RDP_sort.py` — Entry **10**
- `python_src/toolbox/DEM/spm_set_costs.py` — Entry **11**
- `python_src/toolbox/DEM/spm_mdp2rdp.py` — Entry **11**
- `python_src/toolbox/DEM/spm_mdp2rdp_a.py` — Entry **11** (Dirichlet branch)
- `python_src/toolbox/DEM/spm_O2rgb.py` — visualization-adjacent (pong RGB); listed for Entry **2** integration
- `python_src/toolbox/DEM/spm_information_distance.py` — structure-learning support
- `python_src/toolbox/DEM/spm_unique.py`
- `python_src/toolbox/DEM/spm_dir_reduce.py`
- `python_src/toolbox/DEM/spm_MDP_size.py`
- `python_src/toolbox/DEM/spm_MDP_log_evidence.py`
- `python_src/toolbox/DEM/spm_MDP_VB_prune.py`

## A.5 Staged MATLAB mirror (`matlab_src/toolbox/DEM/`) — Entries 1–11 path

- `matlab_src/toolbox/DEM/spm_MDP_pong.m`
- `matlab_src/toolbox/DEM/spm_MDP_generate.m`
- `matlab_src/toolbox/DEM/spm_faster_structure_learning.m`
- `matlab_src/toolbox/DEM/spm_rgm_group.m`
- `matlab_src/toolbox/DEM/spm_merge_structure_learning.m`
- `matlab_src/toolbox/DEM/spm_RDP_basin.m`
- `matlab_src/toolbox/DEM/spm_RDP_compress.m`
- `matlab_src/toolbox/DEM/spm_set_goals.m`
- `matlab_src/toolbox/DEM/spm_RDP_sort.m`
- `matlab_src/toolbox/DEM/spm_set_costs.m`
- `matlab_src/toolbox/DEM/spm_mdp2rdp.m`
- `matlab_src/toolbox/DEM/spm_mdp2rdp_a.m`
- `matlab_src/toolbox/DEM/spm_O2rgb.m`
- `matlab_src/toolbox/DEM/spm_information_distance.m`
- `matlab_src/toolbox/DEM/spm_unique.m`
- `matlab_src/toolbox/DEM/spm_dir_reduce.m`
- `matlab_src/toolbox/DEM/spm_MDP_size.m`
- `matlab_src/toolbox/DEM/spm_MDP_log_evidence.m`
- `matlab_src/toolbox/DEM/spm_MDP_VB_prune.m`
- `matlab_src/toolbox/DEM/spm_MDP_checkX.m` — shared with Entry **12** validation lane
- `matlab_src/toolbox/DEM/spm_parents.m`

## A.6 Oracle tests — core SPM (Phase 0 / shared)

- `tests/oracle/test_spm_cat.py`
- `tests/oracle/test_spm_dot.py`
- `tests/oracle/test_spm_cross.py`
- `tests/oracle/test_spm_softmax.py`
- `tests/oracle/test_spm_log.py`
- `tests/oracle/test_spm_psi.py`
- `tests/oracle/test_spm_dir_norm.py`
- `tests/oracle/test_spm_vec.py`
- `tests/oracle/test_spm_unvec.py`
- `tests/oracle/test_spm_sum.py`
- `tests/oracle/test_spm_zeros.py`
- `tests/oracle/test_spm_betaln.py`
- `tests/oracle/test_spm_cov2corr.py`
- `tests/oracle/test_spm_KL_dir.py`
- `tests/oracle/test_spm_length.py`
- `tests/oracle/test_spm_check_version.py`
- `tests/oracle/test_spm_combinations.py`
- `tests/oracle/test_spm_kron.py`
- `tests/oracle/test_spm_speye.py`
- `tests/oracle/test_spm_Gcdf.py`
- `tests/oracle/test_spm_MDP_MI.py`
- `tests/oracle/test_spm_dir_MI.py`

## A.7 Oracle tests — DEM toolbox (Entries 1–11)

- `tests/oracle/toolbox/DEM/test_spm_MDP_pong.py` — Entry **2**
- `tests/oracle/toolbox/DEM/test_spm_MDP_generate.py` — Entries **1**, **3**
- `tests/oracle/toolbox/DEM/test_spm_MDP_pong_generate_integration.py` — Entries **2–3**
- `tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py` — Entry **4**
- `tests/oracle/toolbox/DEM/test_spm_faster_structure_learning_locals.py` — Entry **4** locals
- `tests/oracle/toolbox/DEM/test_spm_rgm_group.py` — Entry **4**
- `tests/oracle/toolbox/DEM/test_spm_merge_structure_learning.py` — Entry **7**
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry5.py` — Entry **5**
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry6.py` — Entry **6**
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry7.py` — Entry **7**
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry7_full_sequence.py` — Entry **7**
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry8.py` — Entry **8**
- `tests/oracle/toolbox/DEM/test_spm_RDP_basin.py` — Entry **9**
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry9.py` — Entry **9**
- `tests/oracle/toolbox/DEM/test_spm_RDP_sort.py` — Entry **10**
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry10.py` — Entry **10**
- `tests/oracle/toolbox/DEM/test_spm_set_costs.py` — Entry **11**
- `tests/oracle/toolbox/DEM/test_spm_mdp2rdp.py` — Entry **11** (+ shared nested compare)
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry11.py` — Entry **11** smoke
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_full_staged_atari_ledger_1_11.py` — **FSL 1–11 gate**
- `tests/oracle/toolbox/DEM/fsl_1_11_compare_ctx_pkl_to_mat.py` — **Validation 1–11**
- `tests/oracle/toolbox/DEM/test_spm_O2rgb.py`
- `tests/oracle/toolbox/DEM/test_spm_information_distance.py`
- `tests/oracle/toolbox/DEM/test_spm_unique.py`
- `tests/oracle/toolbox/DEM/test_spm_dir_reduce.py`
- `tests/oracle/toolbox/DEM/test_spm_MDP_size.py`
- `tests/oracle/toolbox/DEM/test_spm_MDP_log_evidence.py`
- `tests/oracle/toolbox/DEM/test_spm_MDP_VB_prune.py`
- `tests/oracle/toolbox/DEM/test_spm_parents.py`
- `tests/oracle/toolbox/DEM/test_spm_MDP_checkX.py` — shared checkX (Entry **12** lane uses same module)
- `tests/oracle/toolbox/DEM/conftest.py` — DEM test fixtures/config

## A.8 Oracle test support — MATLAB ref scripts (Entry 4 / grouping)

- `tests/oracle/toolbox/DEM/matlab_ref/oracle_spm_group.m`
- `tests/oracle/toolbox/DEM/matlab_ref/oracle_spm_structure_fast.m`

## A.9 MATLAB custom — capture / dump (Entries 1–11)

- `matlab_custom/dump_rdp_DEM_AtariIII_FSL_1_11.m` — **MATLAB dump 1–11** → `DEMAtariIII_fsl_1_11_rdp.mat`
- `matlab_custom/dump_rdp_DEM_AtariIII.m` — alternate dump (different τ/outers; not FSL gate)
- `matlab_custom/DEM_AtariIII_dump.m`
- `matlab_custom/dump_rdp_DEM_chaos_compression.m`
- `matlab_custom/DEM_chaos_compression_custom.m`
- `matlab_custom/compare_saved_rdp_DEM_chaos_AtariIII.m`
- `matlab_custom/saved_rdp_DEM_AtariIII.mat` — referenced saved RDP (when present)
- `matlab_custom/capture_DEM_AtariIII_entry12_pre_post_XXX.m` — boundary capture around XXX (ledger context)
- `matlab_custom/dump_pdp_DEM_AtariIII_XXX_12_from_fsl_rdp.m` — XXX PDP dump helper

## A.10 Fixtures (Entries 1–11)

- `tests/oracle/toolbox/DEM/fixtures/.gitkeep`
- `tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat` — MATLAB FSL nested **RDP**
- `tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_ctx.pkl` — Python FSL full `ctx` (written on successful FSL pytest)

## A.11 Run logs and compare tees (Entries 1–11)

- `matlab_custom/fsl_1_11_compare_ctx_pkl_to_mat_output.txt` — Validation **1–11** tee
- `matlab_custom/test_DEM_AtariIII_full_staged_atari_ledger_1_11_output.txt` — FSL pytest tee

## A.12 Checkpoint artifact naming (Entries 5–10; under `tests/oracle/toolbox/DEM/_checkpoint_data/`)

Patterns (individual files may exist only after capture builds):

- `atari_entry/dem_atari_entry5_{pre|post}_<tag>.pkl`
- `atari_entry/dem_atari_entry6_{pre|post}_<tag>.pkl`
- `atari_entry/dem_atari_entry7_{pre|post}_<tag>.pkl`
- `atari_entry/dem_atari_entry8_{pre|post}_<tag>.pkl`
- `atari_entry/dem_atari_entry8_oracle_capture_t<training_t>_outer<n_outer>_<tag>.pkl`
- `atari_entry/dem_atari_entry9_oracle_capture_t<training_t>_outer<n_outer>_<tag>.pkl`
- `atari_entry/dem_atari_entry10_sort_capture_t<training_t>_outer<n_outer>_<tag>.pkl`
- `fsl_rgm_mi_workload_full_native_mi.pkl`
- `fsl_rgm_mi_mismatch_corpus_live.pkl`
- `fsl_rgm_spectral_workload_initial.pkl`
- `fsl_link_mi_workload*.pkl`
- `tests/oracle/toolbox/DEM/_tmp_link_mi/` — diagnostic JSON from link-MI work

## A.13 Logs

- `logs/log_0.md` — iteration trace (not sign-off contract)

---

# Appendix B — Files associated with Entry 12

Entry **12** adds the VB solver oracle lane, MATLAB dump fork, RNG audit, compare-lane module, and banded subentry fixtures (**12A–12I**).

## B.1 Policy and subgoal docs

- `Atari_example.md` — § Entry **12** (framework, four scripts, Validation **12**, final-stage review)
- `12DEF.md` — living **12D–12F** status
- `12DEF-archive.md` — archived deep log
- `rules/rgms-rules.mdc` — Entry **12** mandatory blocks
- `rules/entry12-atari-framework.mdc` — Entry **12** agent trigger summary

## B.2 Python implementation — VB core and extracted helpers

- `python_src/toolbox/DEM/spm_MDP_VB_XXX.py` — **primary translation** (~2800-line MATLAB counterpart)
- `python_src/toolbox/DEM/spm_forwards.py` — extracted from XXX local functions
- `python_src/toolbox/DEM/spm_backwards.py` — extracted ( **12G** / `OPTIONS.B=1` path)
- `python_src/toolbox/DEM/spm_VBX.py`
- `python_src/toolbox/DEM/spm_induction.py`
- `python_src/toolbox/DEM/spm_MDP_BMR.py`
- `python_src/toolbox/DEM/spm_edges.py`
- `python_src/toolbox/DEM/spm_index.py`
- `python_src/toolbox/DEM/spm_MDP_checkX.py` — checkX + Entry **12** validation/transform lane
- `python_src/toolbox/DEM/spm_parents.py` — hierarchical parent helpers (12F context)
- `python_src/toolbox/DEM/entry12_matlab_capture.py` — **compare lane**, causal payloads, align helpers, paths, canonical tag

## B.3 Staged MATLAB mirror — Entry 12

- `matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`
- `matlab_src/toolbox/DEM/spm_forwards.m`
- `matlab_src/toolbox/DEM/spm_backwards.m`
- `matlab_src/toolbox/DEM/spm_VBX.m`
- `matlab_src/toolbox/DEM/spm_induction.m`
- `matlab_src/toolbox/DEM/spm_MDP_BMR.m`
- `matlab_src/toolbox/DEM/spm_edges.m`
- `matlab_src/toolbox/DEM/spm_index.m`

## B.4 MATLAB custom — Entry 12 four-script chain and fork

- `matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m` — script **1b** driver
- `matlab_custom/entry12/spm_MDP_VB_XXX_entry12_dump.m` — instrumented MATLAB VB + checkpoints
- `matlab_custom/entry12/README_entry12_matlab_capture.md`
- `matlab_custom/entry12/entry12_matlab_count_rand_draws.m`
- `matlab_custom/entry12/rand.m` — scalar draw helper for audit
- `matlab_custom/entry12/rgms_entry12_rand_scalar.m`
- `matlab_custom/entry12/entry12_VB_matlab_buf_replay.m`
- `matlab_custom/entry12/entry12_VB_matlab_src_buf_replay.m`
- `matlab_custom/entry12_draw_index_audit.py` — RNG draw audit (sign-off gate)
- `matlab_custom/entry12_draw_index_audit_results.json`
- `matlab_custom/entry12_preflight_last.log`
- `matlab_custom/entry12_dump_last.log`
- `matlab_custom/entry12_dump_run_output.txt`
- `matlab_custom/capture_DEM_AtariIII_entry12_pre_post_XXX.m`

### B.4.1 MATLAB custom — Entry 12 research / debug (non-sign-off; do not use for Phase 1 exit proof)

- `matlab_custom/_diag_entry12_causal_boundaries.py`
- `matlab_custom/_diag_12f_value_assert.py`
- `matlab_custom/_diag_entry12_child_Y_out_t1.py`
- `matlab_custom/_diag_entry12_12e_out_t2_child.py`
- `matlab_custom/_diag_child2_P_trace.py`
- `matlab_custom/_diag_child2_P_trace.json`
- `matlab_custom/_diag_child_E_empirical_t2.py`
- `matlab_custom/_diag_child_hier_pre_vb_t2.py`
- `matlab_custom/_diag_child_us_out_t2.py`
- `matlab_custom/_diag_child_fields_out_t2.py`
- `matlab_custom/_diag_child_ED_out_t1.py`
- `matlab_custom/_diag_child_P_mat_only.py`
- `matlab_custom/_diag_12E_O3_fixtures.py`
- `matlab_custom/_diag_child_QO_width.py`
- `matlab_custom/_diag_isolated_child_vb.py`
- `matlab_custom/_diag_child_before_t2.py`
- `matlab_custom/_diag_parent_Q_out_t2.py`
- `matlab_custom/_diag_12E_O3_childP.py`
- `matlab_custom/_diag_O_g4_timeline.py`
- `matlab_custom/_diag_O_g4_writes.py`
- `matlab_custom/_diag_entry12_matlab_spm_parents_child.m`
- `matlab_custom/entry12_compare_op_t2.m`
- `matlab_custom/_tmp_compare_op_t2.m`
- `matlab_custom/entry12_vbx_t2_from_fixtures.m`
- `matlab_custom/_tmp_vbx_t2_inputs_from_fixtures.py`
- `matlab_custom/_tmp_vbx_t2_compare.py`
- `matlab_custom/_tmp_vbx_fixture_parity.py`
- `matlab_custom/_tmp_vbx_fixture_parity.json`
- `matlab_custom/_tmp_vbx_phase_q_parity.py`
- `matlab_custom/_tmp_vbx_phase_q_parity.json`
- `matlab_custom/entry12_12f_vbx_F_probe.py`
- `matlab_custom/entry12_12f_vbx_F_probe.json`
- `matlab_custom/entry12_12f_P_trace_probe.py`
- `matlab_custom/entry12_12f_P_trace_probe.json`
- `matlab_custom/entry12_12f_P_F_probe.py`
- `matlab_custom/entry12_12f_P_F_probe.json`
- `matlab_custom/entry12_12f_vbx_t2_from_mat.m`
- `matlab_custom/entry12_12f_vbx_t2_pre_fwd_from_mat.m`
- `matlab_custom/entry12_12f_vbx_t2_crosslane.py`
- `matlab_custom/entry12_12f_M_row_probe.py`
- `matlab_custom/entry12_12f_M_row_probe.json`
- `matlab_custom/entry12_12f_read_mat_F.m`
- `matlab_custom/entry12_12f_paired_probe.py`
- `matlab_custom/entry12_12f_paired_probe_results.json`
- `matlab_custom/entry12_12f_induction_compare.py`
- `matlab_custom/entry12_12f_induction_compare.m`
- `matlab_custom/entry12_12f_induction_compare_results.json`
- `matlab_custom/entry12_12f_induction_internals.py`
- `matlab_custom/entry12_12f_induction_internals.json`
- `matlab_custom/entry12_12f_run_matlab_induction.py`
- `matlab_custom/entry12_12f_live_forwards_audit.py`
- `matlab_custom/entry12_12f_snap_forwards_replay.py`
- `matlab_custom/entry12_12f_belief_dot_audit.py`
- `matlab_custom/entry12_12f_g_compare.py`
- `matlab_custom/entry12_12f_state_audit.py`
- `matlab_custom/entry12_12f_frozen_dot_probe.py`
- `matlab_custom/entry12_12f_frozen_dot_probe.m`
- `matlab_custom/entry12_matlab_frozen_g_terms.m`
- `matlab_custom/entry12_run_matlab_frozen_g_terms.py`
- `matlab_custom/entry12_matlab_rand_count.py`
- `matlab_custom/entry12_matlab_rand_count_results.json`
- `matlab_custom/entry12_buf_replay_compare.py`
- `matlab_custom/entry12_buf_replay_compare_results.json`
- `matlab_custom/entry12/entry12_bf_I_goal_compare.m`
- `matlab_custom/entry12_bf_I_compare.py`
- `matlab_custom/entry12/entry12_induction_internals_from_mat.m`
- `matlab_custom/entry12/entry12_spm_induction_internals.m`
- `matlab_custom/entry12/entry12_induction_only_probe.m`
- `matlab_custom/entry12/entry12_spm_induction.m`
- `matlab_custom/_evidence_12f_g_decomposition.py`
- `matlab_custom/_evidence_id_hid_shape.py`
- `matlab_custom/_evidence_matlab_h_ih.py`
- `matlab_custom/_evidence_matlab_vb_g1.py`
- `matlab_custom/XXX_12_causal_run_stderr.txt`
- `matlab_custom/xxx12_rerun_stderr.log`

## B.5 Oracle tests — Entry 12 (script **3**, **4**, subentries)

- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_XXX_12.py` — script **3** (XXX 12)
- `tests/oracle/toolbox/DEM/XXX_12_compare_pdp_pkl_to_mat.py` — script **4** (Validation **12**)
- `tests/oracle/toolbox/DEM/entry12_preflight_vb_rand_k.py` — script **1a** (preflight `K`)
- `tests/oracle/toolbox/DEM/entry12_loadmat_convert.py` — `.mat` → nested Python
- `tests/oracle/toolbox/DEM/test_entry12_matlab_capture_loader.py`
- `tests/oracle/toolbox/DEM/test_entry12_canonical_mats_oracle.py`
- `tests/oracle/toolbox/DEM/test_entry12_q_y_flatten_order.py`
- `tests/oracle/toolbox/DEM/test_entry12_vb_atari_probe.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12.py` — driver / segment tests
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12A.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12B.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12C.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12D.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12E.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12F.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12GHI.py` — **12G** informational
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12_driver.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12_handoff_capture.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12_segment_atof.py`
- `tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12_segment_atoc.py`
- `tests/oracle/toolbox/DEM/_entry12_handoff_assert.py`
- `tests/oracle/toolbox/DEM/test_spm_forwards.py`
- `tests/oracle/toolbox/DEM/test_spm_backwards.py`
- `tests/oracle/toolbox/DEM/test_spm_VBX.py`
- `tests/oracle/toolbox/DEM/test_spm_induction.py`
- `tests/oracle/toolbox/DEM/test_spm_MDP_BMR.py`
- `tests/oracle/toolbox/DEM/test_spm_edges.py`
- `tests/oracle/toolbox/DEM/test_spm_index.py`
- `tests/oracle/toolbox/DEM/test_spm_mdp2rdp.py` — shared nested compare (12 input **RDP**, final **PDP**)

## B.6 Fixtures — Entry 12 (`tests/oracle/toolbox/DEM/fixtures/`)

- `DEMAtariIII_entry12_vb_matlab_rand_buf.mat` — MATLAB RNG buffer (replay)
- `entry12_vb_rand_K.mat` — preflight K artifact
- `DEMAtariIII_XXX_12_rdp.mat` — oracle input **RDP** (from FSL `.mat` lane)
- `DEMAtariIII_XXX_12_rdp.pkl`
- `DEMAtariIII_XXX_12_pdp.mat` — final **PDP** MATLAB
- `DEMAtariIII_XXX_12_pdp.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12A.mat`
- `DEMAtariIII_entry12_rgms_canonical_12A.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12B.mat`
- `DEMAtariIII_entry12_rgms_canonical_12B.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12C.mat`
- `DEMAtariIII_entry12_rgms_canonical_12C.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12D.mat`
- `DEMAtariIII_entry12_rgms_canonical_12D.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12E.mat`
- `DEMAtariIII_entry12_rgms_canonical_12E.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12F.mat`
- `DEMAtariIII_entry12_rgms_canonical_12F.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12G.mat`
- `DEMAtariIII_entry12_rgms_canonical_12G.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12H.mat`
- `DEMAtariIII_entry12_rgms_canonical_12H.pkl`
- `DEMAtariIII_entry12_rgms_canonical_12I.mat`
- `DEMAtariIII_entry12_rgms_canonical_12I.pkl`

(Other `run_tag` values may exist locally; canonical sign-off tag is **`rgms_canonical`**.)

## B.7 Run logs and compare tees (Entry 12)

- `matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt` — **authoritative Validation 12 tee**
- `matlab_custom/test_DEM_AtariIII_XXX_12_output.txt` — script **3** pytest tee

## B.8 Optional monitoring (Entry 12 debug)

- `matlab_custom/vb_12_monitor_spm_MDP_VB_XXX_from_fsl_rdp.m` (when present)
- `matlab_custom/vb_12_monitor_spm_MDP_VB_XXX_from_fsl_rdp_output.txt` (when present)

---

## Document maintenance

When adding entries, fixtures, or changing sign-off contracts:

1. Update this file’s **§4 status** and **§6 discrepancies**.
2. Append new paths to **Appendix A** or **B** (do not remove historical debug paths from B.4.1 without archive note).
3. Keep `Atari_example.md` status bullets in sync with the latest **3 → 4** tee (historical bullets may lag; tee wins).

---

*End of `translation_framework_1to12.md`.*
