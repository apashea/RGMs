# Entry 12 MATLAB subentry `.mat` capture

**Goal (project):** Prove Python **`spm_MDP_VB_XXX.py`** matches MATLAB VB on the Atari FSL **`RDP`**. Sign-off is script **4** (**`XXX_12_compare_pdp_pkl_to_mat.py`**) exit **0** on paired **1b**/**3** fixtures — see **`Atari_example.md`** § **Entry 12 — Goal vs means (agent anchor)**.

**This folder is instrumentation only** — capture fork and driver for **`.mat`** fixtures, not the translation target.

This folder implements the Entry 12 plan in `Atari_example.md`: **one** MATLAB driver run loads the canonical nested **`RDP`**, performs **`spm_MDP_checkX`**, and walks the instrumented variational-BP fork so that **all** spine checkpoints **`DEMAtariIII_entry12_<runTag>_12A.mat` … `_12I.mat`** are written under a single output directory in **one** execution.

## Prerequisites

- SPM / `matlab_src` DEM toolbox on the MATLAB path (same as other RGMs MATLAB work).
- A file **`saved_rdp_DEM_AtariIII.mat`** containing variable **`RDP`**, produced by running **`matlab_custom/dump_rdp_DEM_AtariIII.m`** (ledger-aligned chain through `RDP.T = 64`). Default lookup path: **`matlab_custom/saved_rdp_DEM_AtariIII.mat`** (beside `dump_rdp_DEM_AtariIII.m`).

## Running capture (MATLAB)

From the repo root (adjust `cd`):

```matlab
addpath(genpath('matlab_src'));
addpath(genpath('matlab_custom'));
cd matlab_custom/entry12;
DEMAtariIII_entry12_dump_all_subentries();
```

Optional environment **before** starting MATLAB:

| Variable | Meaning |
|----------|---------|
| `RGMS_ENTRY12_CAPTURE_RUN_TAG` | Filename token (default `default`). |
| `RGMS_ENTRY12_CAPTURE_OUT_DIR` | Output directory (default `matlab_custom/entry12/out`). |
| `RGMS_ENTRY12_CAPTURE_RDP_MAT` | Absolute path to `RDP` `.mat` if not using default `saved_rdp_DEM_AtariIII.mat`. |

### Canonical tag for pinned Python oracles

Python uses **`ENTRY12_CANONICAL_RUN_TAG`** (default **`rgms_canonical`**, override with env **`RGMS_ENTRY12_CANONICAL_RUN_TAG`**) when resolving paths such as **`entry12_subentry_mat_path_canonical(...)`**. To produce mats that match those paths in MATLAB, set the capture tag before dumping:

```matlab
setenv('RGMS_ENTRY12_CAPTURE_RUN_TAG', 'rgms_canonical');
DEMAtariIII_entry12_dump_all_subentries();
```

If you keep MATLAB’s default tag **`default`**, set **`RGMS_ENTRY12_CAPTURE_RUN_TAG=default`** when running pytest so Python looks under the same filenames.

## What gets written

| File | Role |
|------|------|
| `_12A.mat` | **`MDP`** after `spm_MDP_checkX`, **`OPTIONS`**, **`meta`**. |
| `_12B.mat` | Post-setup workspace bundle (`process`, `GP`, `id`, counts, …). |
| `_12C.mat` | Pre-`for t` tensors (`M`, `O`, priors, `BP`/`IP`, …). |
| `_12D.mat` | Lean boundaries **`in`**, **`out_t1`**, **`out_t2`**, **`out_t3`**, **`out_tT`**; **`out_t1`** may include **`entry12_prechild`**. |
| `_12E.mat` | Same boundary keys; **`O`** at **`t`** plus optional **`nested_y_summary`**. |
| `_12F.mat` | Same boundary keys; parent **`Q`**, **`P`**, **`R`**, **`v`**, **`w`**, **`MDP`**, optional **`nested_y_summary`**, inspection-only **`entry12_phase_log`** (ordered VB phases at this ``t``). |
| `_12G.mat` | After the main time loop, before Dirichlet accumulation assembly. |
| `_12H.mat` | **`PDP`** = assembled output (same logical role as uninstrumented `spm_MDP_VB_XXX`). |
| `_12I.mat` | **`spine`** metadata (`T`, `Nm`, …) for bookkeeping / tooling. |

Nested **child** calls to `spm_MDP_VB_XXX_entry12_dump` do **not** re-emit these files (dumping is disabled on recursion so top-level tags are not overwritten). With **`RGMS_ENTRY12_CAPTURE_Y_PROBE=1`** (default), child VB still records **`entry12_Yfill`** and **`entry12_VBX`** on the nested **`MDP.MDP`** struct inside parent snaps.

## Python loading

Uses `scipy.io.loadmat` **MAT-format v7** (not v7.3 HDF5) — MATLAB `save(..., '-v7')`.

```python
from pathlib import Path
from python_src.toolbox.DEM.entry12_matlab_capture import (
    load_entry12_subentry_mat,
    entry12_subentry_mat_path,
)

p = entry12_subentry_mat_path("default", "12A")
blob = load_entry12_subentry_mat(p)
mdp = blob["MDP"]
```

Use **`rgms_repo_root()`** / **`default_entry12_mat_output_dir()`** if paths must stay portable.

## Implementation files

- **`DEMAtariIII_entry12_dump_all_subentries.m`** — single user-facing runner (default **`OPTIONS`** as local function; loads **`RDP`** without mutating it before **`spm_MDP_checkX`**).
- **`spm_MDP_VB_XXX_entry12_dump.m`** — fork of `spm_MDP_VB_XXX.m` with third argument **`dumpSpec`** and checkpoint saves.
