# Phase 2 — `ctx["RDP"]` → MATLAB-struct bridge characterization

**Date:** 2026-05-28  
**Step:** Deliberate sequence **2** (after Entry **12** freeze, before **`rdp_ctx_to_matlab_struct`** implementation)  
**Policy:** `Atari_example.md` § **Entry 12 Phase 1 — frozen; Atari Phase 2 deliberate sequence**

---

## Goal

Characterize **structural and container-type** deltas between:

| Source | Path |
|--------|------|
| Python FSL ledger output | `ctx["RDP"]` in `tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_ctx.pkl` |
| MATLAB FSL reference (type template) | `tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat` → `mat_nested_to_py(loadmat(...))["RDP"]` |

**Out of scope for the bridge numeric fight:** accepted ENTRY **1–11** ledger extent drift (**`511`** Python vs **`485`** MATLAB on top-level **`A`**, **`H`**, **`B`**). Bridge must **preserve Python extents** in stored values while aligning **container types** to the MATLAB template.

**Entry 12 validation lane reference (frozen — do not change for Phase 2):**

- VB compute: `entry12_rdp_for_vb_from_mat_nested` — `spm_MDP_checkX(..., transform=False)` only.
- Validation / FSL compare: `entry12_rdp_for_validation_from_mat_nested` — checkX then `_spm_MDP_checkX_transform_align` against raw **`.mat`** nested template (`entry12_matlab_capture.py`).

Phase **2** bridge should produce a nested **`RDP`** that, after the same checkX + transform-align pattern against the FSL **`.mat`** template, is type-compatible with what Entry **12** expects from frozen **`.mat`** dumps — but with **Python ledger numbers**.

---

## Instrument

```powershell
cd C:\Users\andre\.cursor\RGMs
conda activate rgms
python tests/oracle/toolbox/DEM/fsl_1_11_compare_ctx_pkl_to_mat.py --report-type-mismatches-only
```

**Latest run:** exit **0** (type report only; parity assert skipped). Tee: `matlab_custom/fsl_1_11_compare_ctx_pkl_to_mat_output.txt`.

**Summary line:** `type walk: 208 mismatch line(s)` (2026-05-28 refresh).

**Top-level key diff:** `only_in_PKL=(none); only_in_MATLAB=(none)` — same field set at **`RDP`** root.

**checkX schema:** both trees pass coarse schema (non-strict); PKL and MATLAB differ in representation, not missing mandatory top-level keys.

---

## Coarse schema contrast (top-level `RDP`)

| Field | PKL (`ctx["RDP"]`) | MATLAB (`.mat`) | Bridge note |
|-------|--------------------|-----------------|-------------|
| **`A{g}`** | `list`, dense `ndarray`, **511** cols | `list`, **`csc_array`**, **485** cols | Sparse + extent (extent accepted policy) |
| **`B`** | `list(len=1)` → `ndarray(511,511,6)` | bare `ndarray(485,485,6)` | List wrapper vs bare 3-D tensor; extent |
| **`C{g}`** | `ndarray(ng, 1)` column | `ndarray(ng,)` 1-D | Shape layout at same modality count |
| **`G`** | `dict` (keyed sub-structs) | `ndarray(14,)` **`uint8`** | Container class + semantics |
| **`H{1}`** | dense `ndarray(511,1)` | **`csc_array(485,1)`** | Sparse + extent |
| **`T`** | `float` (64.0) | `int` (64) | Scalar dtype |
| **`U`** | `ndarray(1,1)` **`bool`** | scalar `int` (1) | Matrix vs scalar; bool vs int |
| **`sA`, `sC`** | `list` of `int` | `ndarray` **`uint8`** | List vs vector |
| **`sB`** | `list(len=1)` of `int` | scalar `int` | List wrapper vs scalar |
| **`id.A{g}`** | `ndarray(1,1)` **`float64`** | scalar `int` | 1×1 matrix vs scalar |
| **`id.cid`** | empty `list` | empty `ndarray(0,)` **`uint8`** | Empty container type |
| **`id.hid`** | `list` len **22** | `ndarray(25,)` **`uint16`** | Length + container (upstream 1–11; not resized in bridge) |
| **`ss.*`** | nested `list` len **4** | nested `list` len **16** | Structural nesting depth (policy: characterize; do not “fix” 1–11 extents) |

Nested **`RDP.MDP`** ( **`L=1`** child) shows the same pattern classes at finer granularity (111 modalities, 60 factors).

---

## Mismatch taxonomy (for bridge design)

### Category A — Accepted ledger extent (do not fight in bridge)

Paths under top-level **`A`**, **`H`**, and top-level **`B`** where shapes jointly include **511** and **485**. Tagged in compare output as **`[accepted ledger dim 511 vs 485 - upstream Py/MATLAB; ENTRY 1-11 policy]`**.

**Bridge rule:** keep Python **511**-wide tensors; when converting to **`csc_array`**, use **511**-column sparse shapes derived from Python dense data — **not** MATLAB **485** slices.

### Category B — Dense vs sparse (same or comparable shape)

| Path pattern | PKL | MATLAB |
|--------------|-----|--------|
| **`RDP.MDP.A[g]`** | dense `ndarray` | **`csc_array`** (many cells) |
| **`RDP.MDP.A[g]`** (selected) | `(5,10)` dense | `(5,5)` or `(5,10)` **`csc_array`** | Some modality slices differ in **second dim** (10 vs 5) — separate from 511/485; treat as upstream 1–11 content, not bridge type coercion |

Top-level **`A`**, **`H`**: Category A + B combined.

**Bridge rule:** convert eligible dense leaves to **`scipy.sparse.csc_array`** (or compare-lane equivalent) matching MATLAB **sparsity pattern class**, at **Python** shapes.

### Category C — List vs `ndarray` vector

| Path | PKL | MATLAB |
|------|-----|--------|
| **`RDP.sA`**, **`RDP.sC`** | `list` | `ndarray` **`uint8`** |
| **`RDP.MDP.sA`**, **`sB`**, **`sC`** | `list` | `ndarray` |
| **`RDP.id.cid`** | `list` (empty) | `ndarray(0,)` |
| **`RDP.id.hid`** | `list` | `ndarray` |

**Bridge rule:** pack lists to **`numpy.ndarray`** with MATLAB dtype width where compare shows **`uint8`** / **`uint16`**.

### Category D — Scalar vs 1×1 matrix vs list-wrapped scalar

| Path | PKL | MATLAB |
|------|-----|--------|
| **`RDP.T`**, **`RDP.MDP.T`** | `float` | `int` |
| **`RDP.U`** | `ndarray(1,1)` bool | scalar `int` |
| **`RDP.sB`** | `list` → `int` | scalar `int` |
| **`RDP.id.A[g]`**, **`RDP.MDP.id.D[f]`**, **`id.E[f]`** | `ndarray(1,1)` float | scalar `int` |
| **`RDP.MDP.B[f]`** (many indices) | `ndarray(1,1)` | scalar `int` |

**Bridge rule:** unwrap 1×1 matrices to scalars where MATLAB has scalars; cast **`T`** to **`int`**; normalize **`U`** to MATLAB scalar convention (compare shows numeric equality after unwrap).

**Entry 12 U policy (already in capture lane):** `_entry12_u_scalar_to_matrix` promotes scalar **`U`** to **`(1,1)`** for checkX — bridge may emit MATLAB-like scalar **`U`** at product boundary; checkX path handles promotion.

### Category E — `dict` vs `list` / `ndarray` (`G`)

| Path | PKL | MATLAB |
|------|-----|--------|
| **`RDP.G`** | `dict(len=1)` keyed | `ndarray(14,)` **`uint8`** |
| **`RDP.MDP.G`** | `dict(len=4)` keyed | `list(len=4)` of nested lists |

**Bridge rule:** **`G`** is not a simple dtype cast — requires MATLAB-faithful **`G`** serialization rules from **`spm_mdp2rdp`** / ledger (step **3** oracle must cite MATLAB structure). Type walk alone insufficient for semantic mapping.

### Category F — Column vs row / rank layout (`C`)

Focused probes: **`C[g]`** often **`(ng, 1)`** PKL vs **`(ng,)`** MATLAB with **max_abs_diff=0** after squeeze-ravel.

**Bridge rule:** optional squeeze to 1-D where MATLAB uses vectors; numeric content unchanged.

### Category G — Nested `ss` list lengths (4 vs 16)

**`RDP.ss.*`** and **`RDP.MDP.ss.*`**: Python nested lists length **4** vs MATLAB **16** with different element types (`list` vs `ndarray`).

**Bridge rule:** defer to ENTRY **1–11** policy — document for product parity; **do not** resize to MATLAB **16** unless user explicitly changes 1–11 acceptance. Phase **2** minimum: type-align **within** Python extents.

---

## Entry 12–specific hooks (bridge must satisfy)

From `entry12_matlab_capture.py` (frozen reference behavior):

1. **`_entry12_u_scalar_to_matrix`** — scalar **`U`** → **`(1,1)`** before checkX when needed.
2. **`_entry12_type_ref_for_transform`** — after checkX, **`id.g`** may need **`(1, ng)`** **`ndarray`** template from checked list form (Validation **12** input **`RDP`** compare uses raw **`.mat`** template).
3. **`entry12_rdp_for_vb_from_mat_nested`** vs **`entry12_rdp_for_validation_from_mat_nested`** — product VB may use checkX-only path; oracle/compare uses validation lane with transform align.

**Bridge acceptance (step 3 preview):**

- Input: **`ctx["RDP"]`** from FSL PKL.
- Reference template: **`DEMAtariIII_fsl_1_11_rdp.mat`** nested **`RDP`** (types only).
- Output: nested dict passing **`fsl_1_11_compare`** type walk **except** Category A lines (511 vs 485) and Category G length policy lines — or explicit documented exceptions in oracle.
- Then: **`entry12_rdp_for_vb_from_mat_nested(bridged)`** runs without type surprises; product **`spm_MDP_VB_XXX`** receives same shape class as frozen Entry **12** **`.mat`** lane.

---

## Numeric parity note (FSL 1–11 full assert)

Full compare **without** `--report-type-mismatches-only` fails at first type mismatch:

`AssertionError: RDP.A[0]: type py=<class 'numpy.ndarray'> mat=<class 'scipy.sparse._csc.csc_array'>`

Focused probes show **`C`**, **`sB`**, **`U`** numeric agreement where types differ only by container. **G** / **`MDP.G`** value dumps in tee should be consulted in step **3** for semantic **`G`** mapping.

---

## Refresh procedure

When FSL fixtures or Entries **1–11** change:

1. Regenerate PKL: `RGMS_ATARI_RUN_FULL_STAGED_LEDGER_1_11=1 pytest tests/oracle/toolbox/DEM/test_DEM_AtariIII_full_staged_atari_ledger_1_11.py -q` (long).
2. Ensure **`DEMAtariIII_fsl_1_11_rdp.mat`** matches MATLAB dump (`matlab_custom/dump_rdp_DEM_AtariIII_FSL_1_11.m`).
3. Re-run compare command above; update **Mismatch taxonomy** counts and any new path patterns in this file.

---

## Next step (deliberate sequence 3)

Implement **`rdp_ctx_to_matlab_struct`** in `python_src/toolbox/DEM/` with oracle test:

- Categories **B–F** first (mechanical container alignment at Python extents).
- Category **E** (`G`) with MATLAB **`spm_mdp2rdp`** / ledger reference.
- Category **A** explicitly no-op on extent.
- Category **G** documented exceptions unless user revises 1–11 policy.

Do **not** modify **`spm_MDP_VB_XXX.py`** or Entry **12** compare lane for bridge work.
