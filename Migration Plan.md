# RGM Python Migration Plan

## Phase 0: External SPM Helpers

All files in this phase are small, self-contained math utilities. Port and unit-test each independently. They live in `spm12/` root or `spm12/toolbox/DEM/`.

### Tier 0 — No `spm_*` dependencies (port in any order, parallelizable)

| #    | File             | Location       | Lines  | What it does                                                                                                 | Needs     |
| ---- | ---------------- | -------------- | ------ | ------------------------------------------------------------------------------------------------------------ | --------- |
| 0.1  | `spm_log.m`      | `spm12/`       | 13     | `max(log(A), -32)` — safe log                                                                                | Unit test |
| 0.2  | `spm_softmax.m`  | `spm12/`       | 27     | `exp(x)/sum(exp(x))` over columns                                                                            | Unit test |
| 0.3  | `spm_dir_norm.m` | `spm12/`       | 29     | Dirichlet normalization: `a / sum(a,1)`. Handles cells recursively.                                          | Unit test |
| 0.4  | `spm_psi.m`      | `spm12/`       | 29     | `psi(a) - psi(sum(a))` — expected log probability under Dirichlet. Uses MATLAB's built-in `psi()` (digamma). | Unit test |
| 0.5  | `spm_cat.m`      | `spm12/`       | 100    | Concatenates cell arrays into matrices, filling empties with sparse zeros.                                   | Unit test |
| 0.6  | `spm_vec.m`      | `spm12/`       | ~57    | Vectorizes any cell/struct/array into a column.                                                              | Unit test |
| 0.7  | `spm_unvec.m`    | `spm12/`       | paired | Inverse of `spm_vec`: reshapes a vector back into the original cell/struct shape.                            | Unit test |
| 0.8  | `spm_dot.m`      | `spm12/`       | 77     | Multidimensional tensor inner product (uses `tensorprod`).                                                   | Unit test |
| 0.9  | `spm_cross.m`    | `spm12/`       | 50     | Multidimensional tensor outer product (uses `bsxfun`).                                                       | Unit test |
| 0.10 | `spm_cov2corr.m` | `spm12/`       | 14     | Covariance matrix to correlation matrix.                                                                     | Unit test |
| 0.11 | `spm_zeros.m`    | `spm12/`       | small  | Creates zero array matching shape.                                                                           | Unit test |
| 0.12 | `spm_betaln.m`   | `spm12/`       | small  | Log multivariate beta function (via `gammaln`).                                                              | Unit test |
| 0.13 | `spm_sum.m`      | `spm12/`       | small  | Sum over specified dimensions.                                                                               | Unit test |
| 0.14 | `spm_MDP_size.m` | `toolbox/DEM/` | 49     | Extracts `(Nf, Ns, Nu, Ng, No)` dimensions from an MDP struct. No `spm_*` calls.                             | Unit test |

### Tier 1 — Depends only on Tier 0

| # | File | Location | Lines | What it does | Depends on | Needs |
|---|------|----------|-------|-------------|-----------|-------|
| 0.15 | `spm_MDP_MI.m` | `spm12/` | 117 | Expected free energy = mutual information minus cost. Contains local subfunction `spm_MI`. | `spm_log`, `spm_cat` | Unit test |
| 0.16 | `spm_KL_dir.m` | `spm12/` | 48 | KL divergence between two Dirichlet distributions. Defines its own local `spm_psi`. | `spm_betaln` | Unit test |
| 0.17 | `spm_information_distance.m` | `toolbox/DEM/` | 54 | Information distance between columns of a likelihood tensor. | `spm_dir_norm`, `spm_cat`, `spm_cov2corr` | Unit test |

### Tier 2 — Depends on Tier 0 + Tier 1

| #    | File                     | Location       | Lines | What it does                                                                                           | Depends on                                                                             | Needs     |
| ---- | ------------------------ | -------------- | ----- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | --------- |
| 0.18 | `spm_unique.m`           | `toolbox/DEM/` | 32    | Finds unique columns of a likelihood tensor by information distance.                                   | `spm_information_distance`                                                             | Unit test |
| 0.19 | `spm_dir_reduce.m`       | `toolbox/DEM/` | 38    | Builds a reduction matrix R that merges similar columns of a Dirichlet tensor (BMR-style compression). | `spm_information_distance`                                                             | Unit test |
| 0.20 | `spm_MDP_log_evidence.m` | `toolbox/DEM/` | small | Log evidence for Bayesian model reduction.                                                             | Likely `spm_KL_dir`, `spm_psi`                                                         | Unit test |
| 0.21 | `spm_MDP_VB_prune.m`     | `toolbox/DEM/` | ~136  | Bayesian model reduction for Dirichlet parameters. MI-based or simple pruning.                         | `spm_MDP_MI`, `spm_MDP_log_evidence`, `spm_psi`, `spm_softmax`, `spm_zeros`, `spm_sum` | Unit test |

**Milestone after Phase 0:** All the mathematical building blocks are in Python and independently tested. Two people can work on Phase 0 in parallel — split by odd/even or by tier.

---

## Phase 1: Path 1 — Fresh Structure Learning

These files build a hierarchical generative model from raw data. They depend only on Phase 0 helpers. Port in the order shown.

| #   | File                              | Lines | What it does                                                                                                                | Depends on (from Phase 0)                                                                                                                                  | Needs                                                                    |
| --- | --------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 1.1 | `spm_rgm_group.m`                 | 123   | Core RG grouping: spectral partition of outcomes by MI, with a size bound. **Start here** — it is small and self-contained. | `spm_cat`, `spm_MDP_MI`                                                                                                                                    | Indirectly tested by Atari/drone demos. **Needs unit test.**             |
| 1.2 | `spm_MB_structure_learning.m`     | ~355  | Builds `MDP{n}` hierarchy from outcomes + spatial locations. Uses `spm_space` (local subfunction) for grouping.             | `spm_unique`, `spm_cat`, `spm_dir_norm` + local subfunctions `spm_structure_fast`, `spm_space`, `spm_time`                                                 | Tested by `DEM_compression`, `DEM_MNIST_RGM`, and all compression demos. |
| 1.3 | `spm_faster_structure_learning.m` | ~517  | Builds `MDP{n}` hierarchy using MI-based partitioning across multiple streams.                                              | `spm_rgm_group` (1.1), `spm_unique`, `spm_dir_norm`, `spm_vec`, `spm_unvec`, `spm_cross`, `spm_cat` + local subfunctions `spm_structure_fast`, `spm_group` | Tested by `DEM_Atari`, `DEM_drone_VI`.                                   |

**Note:** 1.2 and 1.3 are independent of each other (alternative structure learners). We can port them in parallel. Both include local subfunctions (`spm_structure_fast`, etc.) that should be ported as private helpers within the same module.

**Milestone after Phase 1:** We can build hierarchical `MDP{n}` from data. Cannot run end-to-end yet (need conversion + inference).

---

## Phase 2: Common Infrastructure — Hierarchy Conversion

These convert between the flat cell-array `MDP{n}` and the nested `RDP.MDP.MDP...` format. Port in this order.

| #   | File              | Lines | What it does                                                                                                                                                | Depends on     | Needs                                                            |
| --- | ----------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---------------------------------------------------------------- |
| 2.1 | `spm_rdp2mdp.m`   | ~106  | Unpacks nested `RDP.MDP.MDP...` back into `MDP{n}` cell array. Simpler direction — start here.                                                              | `spm_dir_norm` | **Needs unit test.**                                             |
| 2.2 | `spm_mdp2rdp.m`   | ~294  | Converts `MDP{n}` into nested `RDP.MDP.MDP...`. Handles consolidation of unitary mappings, parent linkage. Dispatches to 2.3 when Dirichlet counts present. | `spm_dir_norm` | Tested by every demo.                                            |
| 2.3 | `spm_mdp2rdp_a.m` | ~311  | Dirichlet-count version of 2.2. Called automatically by 2.2 when `MDP{1}.a` exists.                                                                         | `spm_dir_norm` | Indirectly tested. **Needs unit test for the Dirichlet branch.** |

**Validation strategy:** After porting 2.1–2.3, write a round-trip test: build a simple `MDP{n}` → `spm_mdp2rdp` → `RDP` → `spm_rdp2mdp` → `MDP{n}` and verify structural identity.

**Milestone after Phase 2:** We can build a hierarchy and convert it to nested form. Still cannot run inference.

---

## Phase 3: Common Infrastructure — Inference Engine

This is the largest and most complex single file in the entire RGM codebase.

| #   | File               | Lines    | What it does                                                                                                                                                                            | Depends on                                                                                                                                                                                                                                                 | Needs                 |
| --- | ------------------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| 3.1 | `spm_MDP_VB_XXX.m` | **2800** | Variational Bayes active inference solver. Handles nested/hierarchical models. Contains many local subfunctions (`spm_forwards`, `spm_backwards`, `spm_induction`, `spm_action`, etc.). | Nearly all Phase 0 helpers: `spm_softmax`, `spm_log`, `spm_dot`, `spm_cross`, `spm_cat`, `spm_norm`, `spm_psi`, `spm_KL_dir`, `spm_MDP_MI`, `spm_MDP_size`, `spm_vec`, `spm_zeros`, `spm_sample`, `spm_combinations`, `spm_Gcdf`, `spm_kron`, `spm_figure` | Tested by every demo. |

**Strategy for 3.1:** This file is too large to port in one go. Suggested approach:
1. Port the **struct initialization / checking** section first (~lines 1–300)
2. Port the **forward pass** (`spm_forwards` subfunction)
3. Port the **backward pass** (`spm_backwards`)
4. Port **action selection** and **parameter learning**
5. Port **hierarchical recursion** (the part that calls itself for `MDP.MDP`)
6. Validate with `DEM_compression` (simplest end-to-end demo — no learning loop, no streams)

**Note:** `spm_sample` does not exist as a standalone file (glob returned 0 results). It is likely a local subfunction inside `spm_MDP_VB_XXX.m`. Same may apply to `spm_combinations`, `spm_norm`, and a few others. Verify as we port.

**MILESTONE after Phase 3: First end-to-end demo runs.** Use `DEM_compression` or `DEM_sound_compression` — they use only Path 1 + common infrastructure with no learning loops.

---

## Phase 4: Path 3 — Online Belief Update

Two small files that enable the parametric learning loop. Port in this order.

| #   | File               | Lines | What it does                                                                                                            | Depends on                 | Needs                                                                                                                                              |
| --- | ------------------ | ----- | ----------------------------------------------------------------------------------------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4.1 | `spm_RDP_O.m`      | 46    | Injects observations at a target depth inside a nested RDP. Recursive, no external `spm_*` calls. **Tiny, start here.** | Nothing beyond common pool | Tested by `DEM_MNIST_RGM`, `DEM_music_compression`, `DEM_chaos_compression`, `DEM_image_compression`, `DEM_MNIST_compression`, `DEM_MNIST_mixture` |
| 4.2 | `spm_RDP_update.m` | 76    | Writes posterior Dirichlet parameters back into prior model. Optional BMR.                                              | `spm_MDP_VB_prune` (0.21)  | Same demos as above.                                                                                                                               |

**MILESTONE after Phase 4:** Can run the parametric learning loop demos: `DEM_MNIST_RGM` (the best single RGM showcase), `DEM_music_compression`, `DEM_chaos_compression`.

---

## Phase 5: Path 2 — Incremental Structure Merging

These enable growing an existing hierarchy with new data. Port in this order.

| #   | File                             | Lines  | What it does                                                                          | Depends on                                                                      | Needs                                                 |
| --- | -------------------------------- | ------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 5.1 | `spm_get_outcomes.m`             | ~small | Traces outcome indices at the lowest level for given top-level states. Pure indexing. | Nothing                                                                         | **Needs unit test.**                                  |
| 5.2 | `spm_merge_structure_learning.m` | ~300   | Appends new trajectories into an existing `MDP{n}`. Contains local `spm_merge_fast`.  | `spm_unique` (0.18), `spm_dir_norm` (0.3), `spm_cat` (0.5)                      | Tested by `DEM_AtariI`, `DEM_AtariII`, `DEM_AtariIII` |
| 5.3 | `spm_daisy_chain.m`              | 92     | Selective merge: only appends trajectories that end on the attracting set.            | `spm_get_outcomes` (5.1), `spm_merge_structure_learning` (5.2), `spm_cat` (0.5) | Tested by `DEM_AtariI`, `DEM_AtariII`                 |

**MILESTONE after Phase 5:** Can run `DEM_AtariI` (structure learning + incremental merge + inference).

---

## Phase 6: Path 4 — Model Compression & Planning

These reduce the model and add cost/reward signals. Port in this order — the dependency chain is strict.

| #   | File                 | Lines | What it does                                                                                         | Depends on                                                                          | Needs                                   |
| --- | -------------------- | ----- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------- |
| 6.1 | `spm_RDP_compress.m` | ~136  | Applies a reduction matrix R to the top-level, propagates down hierarchy. **Workhorse for 6.2–6.4.** | `spm_dir_norm` (0.3), `spm_dir_reduce` (0.19)                                       | **Needs unit test.**                    |
| 6.2 | `spm_RDP_sort.m`     | 81    | Eigendecomposition of top-level transitions → removes states outside NESS attractor.                 | `spm_dir_norm` (0.3), `spm_RDP_compress` (6.1)                                      | Tested by `DEM_AtariII`, `DEM_AtariIII` |
| 6.3 | `spm_RDP_MI.m`       | ~95   | Merges top-level states while preserving MI between leading and trailing streams.                    | `spm_dir_norm` (0.3), `spm_dir_reduce` (0.19), `spm_RDP_compress` (6.1)             | Tested by `DEM_AtariII`, `DEM_AtariIII` |
| 6.4 | `spm_set_goals.m`    | ~138  | Identifies which top-level states correspond to rewarded/costly outcomes at the bottom.              | Recursive self-call; reads MDP struct fields                                        | Tested by `DEM_AtariII`, `DEM_AtariIII` |
| 6.5 | `spm_RDP_basin.m`    | 69    | Retains only states in basins of attraction toward goal states (absorbing-chain logic).              | `spm_set_goals` (6.4), `spm_RDP_compress` (6.1)                                     | Tested by `DEM_AtariIII`                |
| 6.6 | `spm_set_costs.m`    | ~167  | Propagates cost/reward preferences down the hierarchy as `MDP{n}.C{g}`.                              | Recursive self-call, `spm_dir_norm` (0.3), `spm_MDP_MI` (0.15), `spm_softmax` (0.2) | Tested by `DEM_AtariII`, `DEM_AtariIII` |

**MILESTONE after Phase 6:** Can run `DEM_AtariII` and `DEM_AtariIII` end-to-end.

---

## Phase 7: Visualization Utilities

Nice-to-have for debugging and validation. Not blocking any path. Port in any order.

| #   | File                | Lines | What it does                                                                          | Depends on                                           | Needs                                     |
| --- | ------------------- | ----- | ------------------------------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------- |
| 7.1 | `spm_show_RGB.m`    | ~190  | Visualizes pixel-space outcomes/predictions from inverted deep model with RGB decode. | `spm_cat`, `spm_dir_norm`                            | Tested by Atari, compression, MNIST demos |
| 7.2 | `spm_show_RGM.m`    | ~192  | Visualizes hierarchical states/transitions in raster format.                          | `spm_cat`, `spm_MDP_size`, `spm_dir_norm`, `spm_spy` | Tested by `DEM_drone_VI`                  |
| 7.3 | `spm_RDP_params.m`  | small | Plots transition priors level-by-level.                                               | `spm_rdp2mdp` (2.1)                                  | **Needs unit test.**                      |
| 7.4 | `spm_check_edges.m` | small | Validates parent-index consistency in a nested RDP.                                   | `spm_rdp2mdp` (2.1)                                  | **Needs unit test.**                      |

---
## Demo Breakdown

### Phase 3
These are the first demos we can use once `Path 1 + conversion + spm_MDP_VB_XXX` are working.

#### Path 1 only
- `spm12/toolbox/DEM/DEM_Atari.m`
- `spm12/toolbox/DEM/DEM_drone_VI.m`
- `spm12/toolbox/DEM/DEM_compression.m`
- `spm12/toolbox/DEM/DEM_video_compression.m`
- `spm12/toolbox/DEM/DEM_sound_compression.m`

### Phase 4
These need `Path 3` on top of the Phase 3 stack.

#### Path 1 + Path 3
- `spm12/toolbox/DEM/DEM_music_compression.m`
- `spm12/toolbox/DEM/DEM_chaos_compression.m`
- `spm12/toolbox/DEM/DEM_image_compression.m`
- `spm12/toolbox/DEM/DEM_MNIST_RGM.m`
- `spm12/toolbox/DEM/DEM_MNIST_compression.m`
- `spm12/toolbox/DEM/DEM_MNIST_mixture.m`

### Phase 5
These need `Path 2` on top of the Phase 3 stack.

#### Path 1 + Path 2
- `spm12/toolbox/DEM/DEM_AtariI.m`

### Phase 6
These need `Path 4`, and also rely on earlier phases.

#### Path 1 + Path 2 + Path 4
- `spm12/toolbox/DEM/DEM_AtariII.m`
- `spm12/toolbox/DEM/DEM_AtariIII.m`


---

## Summary: Migration Order at a Glance

```
Phase 0  External helpers (21 files, ~3 tiers, parallelizable within tiers)
  │
Phase 1  Path 1: Structure learning (3 files; 1.2 and 1.3 parallelizable)
  │
Phase 2  Common: Conversion (3 files, strict order)
  │
Phase 3  Common: Inference engine (1 file, 2800 lines, port in subsections)
  │       ── MILESTONE: DEM_compression runs ──
  │
Phase 4  Path 3: Online update (2 small files)
  │       ── MILESTONE: DEM_MNIST_RGM runs ──
  │
Phase 5  Path 2: Incremental merge (3 files, strict order)
  │       ── MILESTONE: DEM_AtariI runs ──
  │
Phase 6  Path 4: Compression & planning (6 files, strict order)
  │       ── MILESTONE: DEM_AtariIII runs ──
  │
Phase 7  Visualization (4 files, any order)
```

**Total files to port:** 43 (21 helpers + 9 path-specific + 9 common/viz + 4 check/diag)
**Total demos for validation:** 14
**Files needing unit tests (no demo coverage):** 12, marked above

---

## Redundant Files — Do Not Port

| File | Reason |
|------|--------|
| `spm_fast_structure_learning.m` | Superseded. No demo calls it. |
| `spm_MDP_structure_learning.m` | Standalone BMR structure learner, not in the RGM pipeline. |
| `spm_RDP_reduce.m` | Dead code — no callers found. |
| `spm_show_WAV.m` | Peripheral audio viz, not RGM. |
| `spm_mdp_a2A.m` | Not called by any RGM code. |
| `spm_get_episodes.m` | Only has commented-out calls. |
| `DEM_greedy_MNIST.m` | Hyperparameter-search wrapper. |
| `DEMO_DCM_MB.m` | DCM stack, not discrete RGM. |
| `DEM_demo_MDP_rule.m` | Older MDP demo, not RGM. |
| `DEM_demo_MDP_maze.m` | Older MDP demo, not RGM. |
| `DEM_thermostat.m` | Uses `spm_MDP_VB_XXX` but not RGM architecture. |
| `DEM_MNIST.m` | Older MNIST demo, not RGM pipeline. |
| `spm_COVID_US.m` | False positive — "renormalise" in normalization sense. |