# 1. Plan

We are translating and validating the non-visual structure-learning path of this MATLAB pipeline:

- `spm_MDP_pong` to build the Pong generative process and stream metadata.
- `spm_MDP_generate` to produce probabilistic outcomes under random actions.
- `spm_faster_structure_learning(PDP.O(:,1:1000), S, Sc)` as the main target.
- Internal dependencies in this path, especially `spm_rgm_group` and `spm_dir_MI`.

The immediate translation goal is Python-native parity for this chain, with MATLAB Engine used only as provisional diagnostic scaffolding where native byte parity is currently blocked by investigated numerical issues.


# 2. Purpose of code

`spm_MDP_pong` constructs a partially observed MDP describing the game world, including observation mappings, transition structure, and identifiers used by later stages. In this workflow it defines the shape and semantics of streams (sensory/reward/cost/policy) and provides consistent inputs to generation and downstream structure learning. Conceptually, this is the source model from which sample trajectories are generated; if this stage is wrong, every later parity check becomes hard to interpret.

`spm_MDP_generate` rolls that model forward stochastically and emits the outcome sequence (`PDP.O`) used by structure learning. Here we enforce replay-controlled comparability (MATLAB `twister` + buffered random draws) so generated windows can be compared before any SL internals are blamed. In other words, this stage isolates whether disagreement originates in generation versus later interpretation of generated outcomes.

`spm_faster_structure_learning` is the core learner under test. It groups outcome channels, builds hierarchical linked structures, and populates nested MDP fields including stream-link metadata (`ss.D`, `ss.E`, `ss.ID`, `ss.IE`). Inside this function, `spm_rgm_group` performs MI-driven grouping with spectral partitioning; later, link assembly computes link-level MI scores through `spm_dir_MI` and stores them into `ss.ID/ss.IE`. The current residual native bottlenecks are located in these two adjacent internal regions.

`spm_rgm_group` computes MI structure over selected stream slices and performs eigensystem-based grouping decisions. In this project, one known bottleneck is spectral ordering sensitivity (MATLAB vs SciPy eig behavior under near-ties), and another is MI assembly parity on runtime `o_sub` slices. These are distinct but coupled: MI values determine eig inputs, and eig ordering determines selected group partitions.

`spm_dir_MI` computes expected information gain for Dirichlet parameters, including the entropy-style core term `H(row) + H(col) - H(joint)`. In the link-storage lane this is where we currently see near-cancellation behavior (Python exact `0.0` vs MATLAB tiny nonzero `~1e-16`) on a matrix that otherwise matches MATLAB bytes. This bottleneck is numerically subtle and currently treated as a separate lane from spectral grouping.


# 3. Current setup and issues

This section follows the original MATLAB snippet order and marks each stage as
validated vs bottleneck, with temporary hooks/checkpoints annotated inline.

Python files involved in this chain (full paths):

- `C:\Users\andre\.cursor\RGMs\python_src\toolbox\DEM\spm_MDP_pong.py`
- `C:\Users\andre\.cursor\RGMs\python_src\toolbox\DEM\spm_MDP_generate.py`
- `C:\Users\andre\.cursor\RGMs\python_src\toolbox\DEM\spm_faster_structure_learning.py`
- `C:\Users\andre\.cursor\RGMs\python_src\toolbox\DEM\spm_rgm_group.py`
- `C:\Users\andre\.cursor\RGMs\python_src\spm_MDP_MI.py`
- `C:\Users\andre\.cursor\RGMs\python_src\spm_dir_MI.py`

Primary test files involved (full paths):

- `C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\test_spm_faster_structure_learning.py`
- `C:\Users\andre\.cursor\RGMs\tests\oracle\test_spm_dir_MI.py`
- `C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\test_spm_MDP_pong_generate_integration.py`
- `C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\test_spm_MDP_generate.py`

Ordered pipeline (from the original snippet):

- `rng(...)` / replay setup for comparable random trajectories.  
  **Validated.** We use MATLAB `twister` + buffered draws replayed into Python so
  the generated path can be compared before blaming SL internals.

- `spm_MDP_pong(...)` (build game generative process and ids).  
  **Validated** for the snippet branch used by these tests.

- Build `S` and helper semantics (`spm_get_hits`, `spm_get_miss` meaning).  
  **Validated for the non-visual lane used here.** This stage is not the current
  parity blocker.

- `spm_MDP_generate(...)` then slice `PDP.O(:,1:k)` / `PDP.O(:,1:1000)`.  
  **Validated.** Pre-SL `O` window parity gates are passing in current setup.

- Visual loop (`spm_figure`, `imshow`, `drawnow`).  
  **Out of scope** for this non-visual parity lane; not part of current bottleneck.

- Enter `spm_faster_structure_learning(...)`:
  - Grouping internals via `spm_rgm_group`:
    - MI assembly lane (`spm_MDP_MI` calls on runtime `o_sub`).  
      **Partially bridged for isolation when needed.** Temporary flag
      `RGMS_FSL_RGM_MATLAB_MI_PUSH=1` rebuilds MI in MATLAB to test whether MI
      assembly is the active blocker.
    - Spectral/eigen grouping lane (group partition from eigensystem).  
      **Current native bottleneck A.** MATLAB vs SciPy eig ordering/tie behavior
      causes earliest group mismatch in native lanes. Temporary flag
      `RGMS_FSL_RGM_MATLAB_EIG=1` injects MATLAB `eig(...,'nobalance')`.

  - Later link stage (`_link_streams`) writes `ss.ID` / `ss.IE` via `spm_dir_MI(a_mat)`.  
    **Current native bottleneck B (later than grouping).** For the failing linked
    matrix, linked `a` bytes match MATLAB, but Python `spm_dir_MI(a)=0` while
    MATLAB gives `~8.88e-16` (near-cancellation lane). Temporary flag
    `RGMS_FSL_LINK_DIR_MI_MATLAB=1` uses MATLAB `spm_dir_MI` only at this link-storage
    call site.

- Exhaustive nested canonical-byte compare (full tree gate).  
  Checkpoint controls:
  - `RGMS_FSL_USE_CHECKPOINT=1`
  - `RGMS_FSL_REFRESH_CHECKPOINT=1` (optional rebuild)  
  Checkpoint purpose is **speed/reproducibility only** (reuse `O_fsl_sx/S_fsl_sx`
  and `o_sl`), not algorithmic behavior change.

Current validated status at this progress point:

- Replay-controlled pre-SL stages are validated.
- Bottleneck ordering is validated: grouping (`spm_rgm_group`) bottleneck appears
  before link `spm_dir_MI`; they are distinct.
- With full temporary bridges at known bottlenecks (Lane D), exhaustive checkpoint
  passes; this confirms no additional unknown downstream blocker in that mode.


# 4. Test Lanes and current evaluation

Lane configurations:

- **Lane A:** exhaustive test with `EIG=0, MI_PUSH=0, LINK=0` (native baseline lane).
- **Lane B:** exhaustive test with `EIG=0, MI_PUSH=1, LINK=0` (MATLAB MI, Python eig).
- **Lane C:** exhaustive test with `EIG=1, MI_PUSH=1, LINK=0` (MATLAB MI + MATLAB eig, native link `spm_dir_MI`).
- **Lane D:** exhaustive test with `EIG=1, MI_PUSH=1, LINK=1` (MATLAB MI + MATLAB eig + MATLAB link `spm_dir_MI`).
- **Lane E:** non-exhaustive subset in this file via `-k "not exhaustive_exact_oracle"` (fast regression lane; not a bottleneck-classification lane).

Current progress toward end goal is substantial but intentionally staged. The harness can now move bottlenecks forward in a controlled way, and lane definitions are stable enough to avoid the prior ambiguity around what is native vs temporarily bridged. In practical terms, we are no longer searching blindly; we can deliberately select a lane and know what class of issue it is expected to expose.

At a broad level, the first unresolved class is spectral grouping parity (native eig path) and the second unresolved class is link-time `spm_dir_MI` near-cancellation. These are adjacent in the pipeline but analytically separable, and the lane outcomes already prove that separation: Lane B remains blocked in grouping, Lane C advances to link MI, and Lane D clears the tree under full provisional bridging.

Going forward, the main work is to convert this lane-based diagnostic certainty into Python-native closure decisions: either achieve stricter numeric equivalence in those two lanes or settle explicit numeric policy where 1:1 float64 parity is not realistically recoverable. The key guardrail is unchanged: temporary Engine hooks remain investigative scaffolding and must not be mistaken for final architecture.
