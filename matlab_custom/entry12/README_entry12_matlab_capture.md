# Entry 12 MATLAB subentry `.mat` capture

**Goal (project):** Faithful, **reusable** Python **`spm_MDP_VB_XXX.py`** for full **`DEM_AtariIII.m`** (four VB call sites), other DEM drivers, and future Python-native simulations. **Phase 1** sign-off is script **4** exit **0** per **`tag`** on paired **1b/3** fixtures. **Current gate:** all four tags green — **`rgms_canonical`**, **`rgms_atari_call2`**, **`rgms_atari_call3`**, **`rgms_atari_call4`**. After shared solver edits, re-run quad-tag **`3→4`**. Authoritative narrative: **`Atari_example.md`** (§ **Multi-tag regression gate**, § **Call 3**, § **Call 4 — captured**).

**This folder is instrumentation only** — capture fork and driver for **`.mat`** fixtures, not the translation target.

This folder implements the Entry 12 plan in `Atari_example.md`: **one** MATLAB driver run loads the canonical nested **`RDP`**, performs **`spm_MDP_checkX`**, and walks the instrumented variational-BP fork so that **all** spine checkpoints **`DEMAtariIII_entry12_<runTag>_12A.mat` … `_12I.mat`** are written under a single output directory in **one** execution (per **`tag`**).

## Prerequisites

- SPM / `matlab_src` DEM toolbox on the MATLAB path (same as other RGMs MATLAB work).
- For **call 1 only** legacy path: **`saved_rdp_DEM_AtariIII.mat`** or FSL fixture (see below).
- For **extended 1b** (call **1** + call **2**): no separate RDP file — driver builds both from **`rng(2)`** inline ledger.

## Running capture (MATLAB)

From the repo root (adjust `cd`):

```matlab
addpath(genpath('matlab_src'));
addpath(genpath('matlab_custom'));
cd matlab_custom/entry12;
DEMAtariIII_entry12_dump_all_subentries();           % default: inline call 1 + call 2
DEMAtariIII_entry12_dump_all_subentries('capture_call3');  % post-NR loop, call 3 only
DEMAtariIII_entry12_dump_all_subentries('capture_call4');  % post-NR loop, call 4 (+ spm_RDP_MI)
```

Optional environment **before** starting MATLAB:

| Variable | Meaning |
|----------|---------|
| `RGMS_ENTRY12_CAPTURE_RUN_TAG` | Filename token (default `default`). Use **`rgms_canonical`**, **`rgms_atari_call2`**, **`rgms_atari_call3`**, or **`rgms_atari_call4`** for pinned oracles. |
| `RGMS_ENTRY12_CAPTURE_OUT_DIR` | Output directory (default `tests/oracle/toolbox/DEM/fixtures`). |
| `RGMS_ENTRY12_CAPTURE_RDP_MAT` | Legacy call-1-only: path to FSL **`RDP`** `.mat` when **`RGMS_ENTRY12_CAPTURE_LEGACY_LOAD=1`**. |
| `RGMS_ENTRY12_CAPTURE_LEGACY_LOAD` | **`1`**: load FSL RDP, dump call **1** only; cannot continue to call **2**. |
| `RGMS_ENTRY12_CAPTURE_SKIP_CALL2` | **`1`**: with legacy load, stop after call **1**. |

### Canonical tag for pinned Python oracles

Python uses **`ENTRY12_CANONICAL_RUN_TAG`** (default **`rgms_canonical`**) when resolving paths. Set **`RGMS_ENTRY12_CAPTURE_RUN_TAG`** to the target tag on **1a**, **1b**, **3**, and **4** (registry: **`entry12_atari_calls.py`**).

## What gets written

| File | Role |
|------|------|
| `_12A.mat` | **`MDP`** after `spm_MDP_checkX`, **`OPTIONS`**, **`meta`**. |
| `_12B.mat` | Post-setup workspace bundle (`process`, `GP`, `id`, counts, …). |
| `_12C.mat` | Pre-`for t` tensors (`M`, `O`, priors, `BP`/`IP`, …). |
| `_12D.mat` | Lean boundaries **`in`**, **`out_t1`**, **`out_t2`**, **`out_t3`**, **`out_tT`**. |
| `_12E.mat` | Same boundary keys; **`O`** at **`t`** plus optional **`nested_y_summary`**. |
| `_12F.mat` | Same boundary keys; parent **`Q`**, **`P`**, **`R`**, **`v`**, **`w`**, **`MDP`**, **`entry12_phase_log`**. |
| `_12G.mat` | After the main time loop, before Dirichlet accumulation assembly. |
| `_12H.mat` | **`PDP`** = assembled output (same logical role as uninstrumented `spm_MDP_VB_XXX`). |
| `_12I.mat` | **`spine`** metadata (`T`, `Nm`, …) for bookkeeping / tooling. |

Nested **child** calls to `spm_MDP_VB_XXX_entry12_dump` do **not** re-emit these files (dumping is disabled on recursion so top-level tags are not overwritten). With **`RGMS_ENTRY12_CAPTURE_Y_PROBE=1`** (default), child VB still records **`entry12_Yfill`** and **`entry12_VBX`** on the nested **`MDP.MDP`** struct inside parent snaps.

## Call-2 generative process (`GA` / `GB` / `GU` / `GD`)

Extended **1b** saves call-2 **`RDP`** with parent **`MDP.GA`** (111 modalities from **`spm_MDP_pong`** via **`GDP.A`**). In MATLAB: **110× `logical`**, **1× `double`** (proprioception **`eye(Nc,Nc)`** when **`Na=true`**). Python **`loadmat`** loses **`logical`** → **`uint8`**; restore via **`entry12_call2_gp_matlab_class.json`** in **`entry12_loadmat_convert.py`** before VB (see **`Atari_example.md`** § **Phase 1b — generative process**). Re-export classes: **`export_call2_gp_class_json.m`**.

## Python loading

Uses `scipy.io.loadmat` **MAT-format v7** (not v7.3 HDF5) — MATLAB `save(..., '-v7')`.

```python
from pathlib import Path
from python_src.toolbox.DEM.entry12_matlab_capture import (
    load_entry12_subentry_mat,
    entry12_subentry_mat_path,
)

p = entry12_subentry_mat_path("rgms_canonical", "12A")
blob = load_entry12_subentry_mat(p)
mdp = blob["MDP"]
```

Use **`rgms_repo_root()`** / **`default_entry12_mat_output_dir()`** if paths must stay portable.

## Phase 1b — four `spm_MDP_VB_XXX` call sites (`DEM_AtariIII.m`)

| Planned `tag` | ~`.m` line | What it is | Status |
|---------------|-----------|------------|--------|
| **`rgms_canonical`** (call **1**) | 217 | Pre-loop VB; FSL ledger; **`RDP.T=64`** | Script **4** exit **0** |
| **`rgms_atari_call2`** | 268 | **First VB inside active-inference loop** (game **1**): **`spm_mdp2rdp(...,0,1/NS)`**, **`T=fix(NT/Ne)`**, **`GDP` process** | Script **4** exit **0** |
| **`rgms_atari_call3`** | 340 | Post-**NR** loop; **`spm_RDP_sort`**, **`T=128`** (no MI) | **`capture_call3`** — script **4** exit **0** (**2026-05-27**) |
| **`rgms_atari_call4`** | 390 | Sort + **`spm_RDP_MI`**, **`T=128`** | **`capture_call4`** — script **4** exit **0** (**2026-05-27**) |

Each new tag requires the same spine (**`12A`–`12I`**, **`RDP`**, **`PDP`**, **`vb_rand_buf`**, **`K`**) and the full **1a → 1b → 3 → 4** chain on that **`tag`** only.

### Call 2 — why and how (summary)

**Why:** Call **2** is the first VB run with generative-process / long-horizon / hierarchical-child semantics that call **1** does not exercise. Proving **`spm_MDP_VB_XXX.py`** only on **`T=64`** FSL is insufficient for **`DEM_AtariIII.m`**.

**How (canonical):** **`DEMAtariIII_entry12_dump_all_subentries.m`** in **one** **`rng(2)`** session:

1. Inline FSL 1–11 → VB capture **`rgms_canonical`**
2. **`entry12_dem_call2_rdp_game1_`** — continue **`DEM_AtariIII.m`** through active-inference setup to **loop index 1** **`RDP`**
3. **`entry12_count_and_save_vb_rand_k_`** → **`entry12_vb_rand_K_rgms_atari_call2.mat`**
4. **`entry12_dump_one_vb_call_`** → **`rgms_atari_call2`** fixtures

**RNG:** **`K`** and **`vb_rand_buf`** are **per tag** — read from paired **`entry12_vb_rand_K_*.mat`** after each refresh; **do not hardcode** historical counts. Python script **3** replays **that tag’s** buffer on **that tag’s** **`RDP.mat`** only. Extended **1b** preserves **DEM state continuity**; it does **not** mean Python re-runs the whole DEM for parity.

**RNG gate (before compute edits):** `matlab_custom/entry12_draw_index_audit.py` (`unused_draws=0`, `sample_calls_match=true`). Site-class investigation: `entry12_compare_sample_traces.py` + MATLAB trace from **1b** — see **`Atari_example.md`** § **primary scripts, wiring, and RNG interconnections**.

**Four-script sign-off per tag:**

| # | Call 2 |
|---|--------|
| **1a** | `entry12_preflight_vb_rand_k.py` with `RGMS_ENTRY12_CAPTURE_RUN_TAG=rgms_atari_call2` |
| **1b** | Extended run above, or `'refresh_call2'` if **`RDP`** frozen |
| **3** | `test_DEM_AtariIII_XXX_12.py` with same tag env |
| **4** | `XXX_12_compare_pdp_pkl_to_mat.py` with same tag env |

**Deprecated:** `build_rdp_DEM_AtariIII_call2_game1.m`, `run_entry12_call2_phase1b.ps1` — not canonical.

**Full documentation:** `Atari_example.md` § **Phase 1b — call 2 (`rgms_atari_call2`)** and § **Entry 12 — primary scripts, wiring, and RNG interconnections**.

## Implementation files

- **`DEMAtariIII_entry12_dump_all_subentries.m`** — user-facing runner: default inline FSL 1–11 + call **1** + call **2**; modes **`capture_call3`** / **`capture_call4`** for post-loop VB appearances.
- **`spm_MDP_VB_XXX_entry12_dump.m`** — fork of `spm_MDP_VB_XXX.m` with third argument **`dumpSpec`** and checkpoint saves.
