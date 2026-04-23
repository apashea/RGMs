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

Three currently tracked bottlenecks (in execution order):

1. `spm_rgm_group` internal MI assembly (`spm_MDP_MI` on runtime `o_sub` slices).
2. `spm_rgm_group` internal spectral sorting/selection (`eig` column ordering +
   `sort(abs(e(:,jmax)),'descend')` sensitivity under near ties).
3. Later `_link_streams` call to `spm_dir_MI(a_mat)` when writing `ss.ID/ss.IE`.

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

- `rng(2)` / replay setup for comparable random trajectories.  
  **Validated.** We use MATLAB `twister` + buffered draws replayed into Python so
  the generated path can be compared before blaming SL internals.

- `[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);` (build game generative process and ids).  
  **Validated** for the snippet branch used by these tests.

- Build `S` and helper semantics (`spm_get_hits`, `spm_get_miss` meaning).  
  **Validated for the non-visual lane used here.** This stage is not the current
  parity blocker.

- `PDP = spm_MDP_generate(GDP);` then slice `PDP.O(:,1:k)` / `PDP.O(:,1:1000)`.  
  **Validated.** Pre-SL `O` window parity gates are passing in current setup.

- Visual loop (`spm_figure`, `imshow`, `drawnow`).  
  **Out of scope** for this non-visual parity lane; not part of current bottleneck.

- `MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);`:
  - Grouping internals via `spm_rgm_group`:
    - MI assembly lane (`spm_MDP_MI` calls on runtime `o_sub`).  
      **Current bottleneck #1.** This is the first internal lane where MI
      reconstruction may diverge before eig is applied. Temporary flag
      `RGMS_FSL_RGM_MATLAB_MI_PUSH=1` rebuilds MI in MATLAB so we can isolate
      this lane (Lane B/C use this).
    - Spectral/eigen grouping lane (group partition from eigensystem).  
      **Current bottleneck #2.** Even when MI is aligned, MATLAB vs SciPy eig
      ordering/tie behavior can change selected group members. Temporary flag
      `RGMS_FSL_RGM_MATLAB_EIG=1` injects MATLAB `eig(...,'nobalance')` to
      isolate this lane.

  - Later link stage (`_link_streams`) writes `ss.ID` / `ss.IE` via `spm_dir_MI(a_mat)`.  
    **Current bottleneck #3 (later than grouping).** For the failing linked
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
- Bottleneck ordering is validated as: `spm_MDP_MI` lane -> spectral sorting lane ->
  later link `spm_dir_MI` lane; these are distinct.
- With full temporary bridges at known bottlenecks (Lane D), exhaustive checkpoint
  passes; this confirms no additional unknown downstream blocker in that mode.


# 4. Test Lanes and current evaluation

Lane configurations:

- **Lane A:** exhaustive test with `EIG=0, MI_PUSH=0, LINK=0` (native baseline lane).
- **Lane B:** exhaustive test with `EIG=0, MI_PUSH=1, LINK=0` (MATLAB MI, Python eig).
- **Lane C:** exhaustive test with `EIG=1, MI_PUSH=1, LINK=0` (MATLAB MI + MATLAB eig, native link `spm_dir_MI`).
- **Lane D:** exhaustive test with `EIG=1, MI_PUSH=1, LINK=1` (MATLAB MI + MATLAB eig + MATLAB link `spm_dir_MI`).
- **Lane E:** non-exhaustive subset in this file via `-k "not exhaustive_exact_oracle"` (fast regression lane; not a bottleneck-classification lane).

Lane-to-bottleneck interpretation (current evidence):

- **Lane A:** native baseline; can fail at bottleneck #1 and/or #2 before reaching #3.
- **Lane B (`MI_PUSH` only):** bypasses bottleneck #1 signal source (MI assembly via MATLAB),
  but still exposes bottleneck #2 (spectral sorting with Python eig).
- **Lane C (`MI_PUSH+EIG`):** bypasses #1 and #2 for isolation and advances to bottleneck #3.
- **Lane D (`MI_PUSH+EIG+LINK`):** bypasses all three currently known bottleneck call sites;
  checkpoint exhaustive passing here means no additional unknown downstream blocker in this mode.
- **Lane E:** does not classify bottlenecks; it is only a quick non-exhaustive regression subset.

Current progress toward end goal is substantial but intentionally staged. The harness can now move bottlenecks forward in a controlled way, and lane definitions are stable enough to avoid the prior ambiguity around what is native vs temporarily bridged. In practical terms, we are no longer searching blindly; we can deliberately select a lane and know what class of issue it is expected to expose.

At a broad level, the first unresolved class is spectral grouping parity (native eig path) and the second unresolved class is link-time `spm_dir_MI` near-cancellation. These are adjacent in the pipeline but analytically separable, and the lane outcomes already prove that separation: Lane B remains blocked in grouping, Lane C advances to link MI, and Lane D clears the tree under full provisional bridging.

Going forward, the main work is to convert this lane-based diagnostic certainty into Python-native closure decisions: either achieve stricter numeric equivalence in those two lanes or settle explicit numeric policy where 1:1 float64 parity is not realistically recoverable. The key guardrail is unchanged: temporary Engine hooks remain investigative scaffolding and must not be mistaken for final architecture.


# 5. Lane-by-lane execution table (A/B/C/D/E) and scientific interpretation

Note on exact harness syntax: in this test harness the MATLAB seed call used for the snippet lane is `rng(0,'twister')` (not `rng(2)`), then `spm_MDP_pong`, `spm_MDP_generate`, and finally `spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc)`.

## Lane A (exhaustive baseline; EIG=0, MI_PUSH=0, LINK=0)

| MATLAB top-line function (run order) | What this function is for (two sentences) | Python syntax used in this codebase | Inner functions relevant at this row | RNG involved? | How our code handles RNG |
|---|---|---|---|---|---|
| `rng(0,'twister')` | This sets MATLAB RNG state deterministically so reference draws are reproducible. It establishes a fixed stochastic baseline before any generation or learning happens. | `with patch("numpy.random.rand", side_effect=_rand_replay_callable(rand_buf)):` | `_matlab_rand_buf_twister_np`, `_rand_replay_callable` | Yes. MATLAB RNG state is explicitly set. | Python does not free-run RNG here; it replays MATLAB-generated random draws in order. |
| `[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);` | This constructs the generative process template (`GDP`) and stream metadata used downstream. It defines model structure but does not yet perform trajectory rollout or structure learning. | `gdp = spm_MDP_pong(nr, nc, nd, na, npix)[0]` | `spm_MDP_pong` internals | RNG context is inherited from the prior seed state. | MATLAB and Python both execute this stage; parity is controlled by deterministic setup and downstream checks. |
| `PDP = spm_MDP_generate(GDP);` | This performs stochastic rollout and produces `PDP.O`, which is the direct input to structure learning. This is the main random-draw consuming stage in the top-line pipeline. | `pdp = spm_MDP_generate(gdp)` | `spm_MDP_generate` internals | Yes. This is the primary random-consumption stage. | Python `numpy.random.rand` is patched to replay MATLAB's buffered draws (`rand_buf`) in exact sequence. |
| `MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);` | This is the target learner under migration and produces the nested `MDP` tree under test. In Lane A this run is Python-native at the known bottleneck call sites. | `mdp_p = spm_faster_structure_learning(o_sl, s_mat, sc)` | `spm_rgm_group` (contains MI/eig grouping path), `_link_streams` (contains `spm_dir_MI` for `ss.ID/ss.IE`) | No new RNG is expected here once `O` is fixed. | Native Python internals are used for MI/eig/link-MI lanes in this lane (no temporary MATLAB bridge callbacks). |

**Final compare strictness (Lane A):** exhaustive canonical-byte nested tree compare via `_assert_mdp_tree_exhaustive_exact(...)` against MATLAB `MDP_fsl_snip_exact`, including field sets, all `a`, all `b`, `T`, `sA/sB/sC`, `id.(A,D,E)`, `G`, and `ss.(D,E,ID,IE)`.

**Scientific meaning of pass/fail (Lane A):**
- Pass: native Python path matches MATLAB exactly at full-tree canonical-byte level for this exhaustive snippet gate.
- Fail: first mismatch localizes the earliest deterministic native divergence in the full pipeline (currently this lane fails at `spm_rgm_group` group bytes, i.e., spectral lane exposure).

## Lane B (exhaustive; EIG=0, MI_PUSH=1, LINK=0)

| MATLAB top-line function (run order) | What this function is for (two sentences) | Python syntax used in this codebase | Inner functions relevant at this row | RNG involved? | How our code handles RNG |
|---|---|---|---|---|---|
| `rng(0,'twister')` | Same seed-setting role as Lane A. It guarantees repeatable MATLAB stochastic references. | Same as Lane A | Same as Lane A | Yes. | Same replay policy as Lane A. |
| `[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);` | Same model-template construction role as Lane A. It prepares the generative structure for rollout and learning. | Same as Lane A | Same as Lane A | In seeded context. | Same as Lane A. |
| `PDP = spm_MDP_generate(GDP);` | Same stochastic rollout role as Lane A. It produces the observation cell used by structure learning. | Same as Lane A | Same as Lane A | Yes. | Same MATLAB-buffer replay policy as Lane A. |
| `MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);` | Same learner call, but Lane B turns on only the MI push bridge for `spm_rgm_group`. This isolates whether MI assembly alone explains the baseline failure. | `mdp_p = spm_faster_structure_learning(o_sl, s_mat, sc, rgm_mi_override_fn=rgm_mi_override_fn)` | `spm_rgm_group` MI matrix rebuilt via MATLAB callback; eig remains Python/SciPy; `_link_streams/spm_dir_MI` remains native Python | No new RNG here once `O` is fixed. | Same deterministic `O`; only MI lane is bridged to MATLAB in Python execution. |

**Final compare strictness (Lane B):** same exhaustive canonical-byte nested tree compare as Lane A.

**Scientific meaning of pass/fail (Lane B):**
- Pass: MI assembly was the dominant blocker and MI bridge resolves full-tree parity.
- Fail: MI-only bridge is insufficient; residual bottleneck remains (observed: still fails at spectral/group ordering boundary in `spm_rgm_group`).

## Lane C (exhaustive; EIG=1, MI_PUSH=1, LINK=0)

| MATLAB top-line function (run order) | What this function is for (two sentences) | Python syntax used in this codebase | Inner functions relevant at this row | RNG involved? | How our code handles RNG |
|---|---|---|---|---|---|
| `rng(0,'twister')` | Same deterministic seed stage as Lane A/B. It anchors comparability of stochastic inputs. | Same as Lane A | Same as Lane A | Yes. | Same replay policy as Lane A/B. |
| `[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);` | Same generative-template stage as prior lanes. It is not where the known residual bottlenecks currently live. | Same as Lane A | Same as Lane A | In seeded context. | Same as prior lanes. |
| `PDP = spm_MDP_generate(GDP);` | Same rollout stage used to construct `PDP.O` input for SL. This stage is kept comparable before isolating SL internals. | Same as Lane A | Same as Lane A | Yes. | Same MATLAB-rand-buffer replay policy as prior lanes. |
| `MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);` | Same learner call, now with MI and eig both bridged in `spm_rgm_group`. This asks what mismatch appears after Step-6 grouping internals are bridged. | `mdp_p = spm_faster_structure_learning(o_sl, s_mat, sc, rgm_eig_pair=rgm_eig_pair, rgm_mi_override_fn=rgm_mi_override_fn)` | `spm_rgm_group` uses MATLAB MI and MATLAB `eig(...,'nobalance')`; `_link_streams/spm_dir_MI` still native Python | No new RNG expected once `O` is fixed. | Same deterministic `O`; MI and eig internals are MATLAB-bridged for isolation. |

**Final compare strictness (Lane C):** same exhaustive canonical-byte nested tree compare as Lane A/B.

**Scientific meaning of pass/fail (Lane C):**
- Pass: once grouping MI/eig are bridged, full-tree parity is recovered, implying no later blocker.
- Fail: first mismatch moves downstream; observed movement to `ss.ID` near-zero MI indicates later link `spm_dir_MI` lane is now exposed as bottleneck.

## Lane D (exhaustive; EIG=1, MI_PUSH=1, LINK=1)

| MATLAB top-line function (run order) | What this function is for (two sentences) | Python syntax used in this codebase | Inner functions relevant at this row | RNG involved? | How our code handles RNG |
|---|---|---|---|---|---|
| `rng(0,'twister')` | Same seed-setting role as other exhaustive lanes. It keeps reference generation reproducible. | Same as Lane A | Same as Lane A | Yes. | Same replay policy as prior exhaustive lanes. |
| `[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);` | Same model setup stage as prior lanes. It provides the structural template for generate and SL. | Same as Lane A | Same as Lane A | In seeded context. | Same as prior lanes. |
| `PDP = spm_MDP_generate(GDP);` | Same stochastic rollout stage. It supplies `PDP.O` input with controlled randomness. | Same as Lane A | Same as Lane A | Yes. | Same MATLAB draw replay into Python as prior exhaustive lanes. |
| `MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);` | Same learner call with all currently known bottleneck bridges active. This is the "if all known isolated bottlenecks are bridged, does exhaustive tree pass" test. | `mdp_p = spm_faster_structure_learning(o_sl, s_mat, sc, rgm_eig_pair=rgm_eig_pair, rgm_mi_override_fn=rgm_mi_override_fn, link_dir_mi_fn=link_dir_mi_fn)` | `spm_rgm_group` MI+eig bridged; `_link_streams` writes `ss.ID/ss.IE` via MATLAB `spm_dir_MI` callback | No new RNG expected once `O` is fixed. | Same deterministic `O`; MI/eig/link-MI are all MATLAB-bridged only at targeted call sites. |

**Final compare strictness (Lane D):** same exhaustive canonical-byte nested tree compare as A/B/C.

**Scientific meaning of pass/fail (Lane D):**
- Pass: full exhaustive tree can be made MATLAB-exact by bridging the currently identified bottleneck call sites, supporting causal localization of native gaps.
- Fail: would indicate additional unknown blockers beyond the three isolated lanes.

## Lane E (non-exhaustive test-scope lane; `-k "not exhaustive_exact_oracle"`)

| MATLAB top-line function (run order) | What this function is for (two sentences) | Python syntax used in this codebase | Inner functions relevant at this row | RNG involved? | How our code handles RNG |
|---|---|---|---|---|---|
| `rng(0,'twister')` (applies in selected integration/snippet tests) | In Lane E this appears where selected tests perform generation-integrated checks. Lane E is a test-selection lane, not an inner-kernel bridge lane. | Same functions as selected tests (`spm_MDP_pong`, `spm_MDP_generate`, `spm_faster_structure_learning`) | Depends on selected test among 5 included tests; one exhaustive gate test is explicitly excluded | Yes in generation-based selected tests. | Same replay policy where generation checks are present. |
| `[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);` | Used by selected non-exhaustive tests to build model inputs. Purpose is fast integration coverage, not full bottleneck classification. | Same as corresponding selected tests | Same as corresponding selected tests | Seeded context where applicable. | Same deterministic/replay setup where those tests require it. |
| `PDP = spm_MDP_generate(GDP);` | Used by selected tests to verify generated `PDP.O` windows before structure learning comparisons. This catches upstream integration regressions quickly. | Same as corresponding selected tests | Same as corresponding selected tests | Yes when generation is exercised. | Same MATLAB-random replay strategy in tests that assert generation parity. |
| `MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);` (or smaller variants in selected tests) | Runs SL in each selected non-exhaustive scenario. Assertions are narrower than exhaustive tree-byte compare and include representative structure checks plus the focused checkpoint eig parity test. | Same function with per-test argument variants | Same internal families, but assertion depth varies by selected test | No new RNG in SL itself once `O` is fixed. | Deterministic given prepared `O`; no special lane-wide bridge semantics beyond each test's own setup. |

**Final compare strictness (Lane E):** not a single exhaustive full-tree byte gate. It is a set of five selected tests (with one deselected exhaustive gate), mixing representative structural checks and one focused Step-6 parity check.

**Scientific meaning of pass/fail (Lane E):**
- Pass: covered non-exhaustive scenarios are currently stable and regressions are not detected in that subset.
- Fail: a covered subpath regressed, but this does not by itself identify exhaustive bottleneck order or certify full native exhaustive parity.

## Scientific interpretation across lanes (bottom-line)

- Lanes A/B/C/D use the same exhaustive final compare target and strictness; only the Python-side inner call-site bridges differ.
- Therefore boundary movement across A->B->C->D is causal evidence, not just incidental test noise.
- Observed pattern supports this bottleneck chain: native grouping/spectral lane first, then link-time `spm_dir_MI` near-cancellation lane.
- Lane E is a fast non-exhaustive control subset; useful for regression hygiene, but not a replacement for exhaustive lane classification evidence.
