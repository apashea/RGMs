# 1. Plan

We are translating and validating the non-visual structure-learning path of this MATLAB pipeline:

- `spm_MDP_pong` to build the Pong generative process and stream metadata.
- `spm_MDP_generate` to produce probabilistic outcomes under random actions.
- `spm_faster_structure_learning(PDP.O(:,1:1000), S, Sc)` as the main target.
- Internal dependencies in this path, especially `spm_rgm_group` and `spm_dir_MI`.

The immediate translation goal is Python-native parity for this chain, with MATLAB Engine used only as provisional diagnostic scaffolding where native byte parity is currently blocked by investigated numerical issues.

The full code snippet we are translating is the first portion of the simulation script in the spm library `\toolbox\DEM\DEM_AtariIII.m` (where we are ignoring the commented-out visualization-specific code as we are focused on reproducing and validating translations the models, operational logic, and results):
```
% set up and preliminaries
%--------------------------------------------------------------------------
rng(2)

% Get game: i.e., generative process (as a partially observed MDP)
%==========================================================================
Nr = 12;                                     % number of rows
Nc = 9;                                      % number of columns
Sc = 9;                                      % scaling
Nd = 4;                                      % random initial conditions
C  = 32;                                     % log cost

% get game in MDP form
%--------------------------------------------------------------------------
[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);

% size of streams
%--------------------------------------------------------------------------
S      = ones(4,3);
S(1,:) = [Nr,Nc,1];                          % sensory stream
S(2,:) = [1 1 1];                            % reward  stream                 
S(3,:) = [1 1 1];                            % cost    stream
S(4,:) = [1 1 1];                            % policy  stream

% reward and cost functions [of outcomes]
%--------------------------------------------------------------------------
spm_get_hits = @(o,id) find(o(id.reward,:)    > 1);
spm_get_miss = @(o,id) find(o(id.contraint,:) > 1);

% Generate (probabilistic) outcomes under random actions
%==========================================================================
%spm_figure('GetWin','Gameplay'); clf

GDP.tau = 1;                                 % smoothness of random paths
GDP.T   = 10000;                             % training length
PDP     = spm_MDP_generate(GDP);             % generate play

% illustrate sequence of random play
%---------------------------------------------------------------------------
%con   = PDP.id.control;
%for t = 1:128
%    subplot(2,1,1)
%    imshow(spm_O2rgb(PDP.O(:,t),RGB))
%    subplot(4,3,8)
%    imshow(PDP.O{con,t}')
%    drawnow
%end

% initial structure learning: grouping operators (iA,iB,iC,...)
%==========================================================================
MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);
```

# 2. Purpose of code

`spm_MDP_pong` constructs a partially observed MDP describing the game world, including observation mappings, transition structure, and identifiers used by later stages. In this workflow it defines the shape and semantics of streams (sensory/reward/cost/policy) and provides consistent inputs to generation and downstream structure learning. Conceptually, this is the source model from which sample trajectories are generated; if this stage is wrong, every later parity check becomes hard to interpret.

`spm_MDP_generate` rolls that model forward stochastically and emits the outcome sequence (`PDP.O`) used by structure learning. Here we enforce replay-controlled comparability (MATLAB `twister` + buffered random draws) so generated windows can be compared before any SL internals are blamed. In other words, this stage isolates whether disagreement originates in generation versus later interpretation of generated outcomes.

`spm_faster_structure_learning` is the core learner under test. It groups outcome channels, builds hierarchical linked structures, and populates nested MDP fields including stream-link metadata (`ss.D`, `ss.E`, `ss.ID`, `ss.IE`). Inside this function, `spm_rgm_group` performs MI-driven grouping with spectral partitioning; later, link assembly computes link-level MI scores through `spm_dir_MI` and stores them into `ss.ID/ss.IE`. The current residual native bottlenecks are located in these two adjacent internal regions.

`spm_rgm_group` computes MI structure over selected stream slices and performs eigensystem-based grouping decisions. In this project, one known bottleneck is spectral ordering sensitivity (MATLAB vs SciPy eig behavior under near-ties), and another is MI assembly parity on runtime `o_sub` slices. These are distinct but coupled: MI values determine eig inputs, and eig ordering determines selected group partitions.

`spm_dir_MI` computes expected information gain for Dirichlet parameters, including the entropy-style core term `H(row) + H(col) - H(joint)`. In the link-storage lane this is where we currently see near-cancellation behavior (Python exact `0.0` vs MATLAB tiny nonzero `~1e-16`) on a matrix that otherwise matches MATLAB bytes. This bottleneck is numerically subtle and currently treated as a separate lane from spectral grouping.


# 3. Current setup and issues

This section follows the ordered MATLAB snippet and states exactly where current
Python-vs-MATLAB mismatches occur in that order. Scope statements in this section
are explicit: when a statement refers to Lane A/B/C/D outcomes, it refers to the
exhaustive selector in `tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py`
function `test_spm_faster_structure_learning_snippet_scale_T1000_exhaustive_exact_oracle`.

Current bottlenecks (ordered by where they occur in the pipeline):

1. `spm_faster_structure_learning` -> `spm_rgm_group` -> MI matrix construction
   from runtime `o_sub`, using `spm_MDP_MI` (Python native path in
   `python_src/spm_MDP_MI.py`).
2. `spm_faster_structure_learning` -> `spm_rgm_group` -> eigen decomposition and
   group ordering at MATLAB-equivalent operations `[e,v] = eig(MI(i,i),...)` and
   `sort(abs(e(:,jmax)),'descend')` (Python native path in
   `python_src/toolbox/DEM/spm_rgm_group.py` using SciPy eig + Python sorting).
3. `spm_faster_structure_learning` -> `_link_streams` -> `spm_dir_MI(a_mat)` when
   writing stream-link scalar maps `ss.ID` and `ss.IE` (Python native path in
   `python_src/spm_dir_MI.py`).

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

- `rng(2)` in snippet intent (harness currently uses `rng(0,'twister')`) and
  replay setup for comparable random trajectories.  
  **Scope and status:** generation parity is controlled by replaying MATLAB random
  draws into Python for the tested path. This is a temporary intervention to hold
  `PDP.O` input comparable while downstream bottlenecks are isolated.

- `[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);` (build game generative process and ids).  
  **Scope and status:** validated for the snippet branch used by this subproject’s
  oracle harness and current test lanes.

- Build `S` and helper semantics (`spm_get_hits`, `spm_get_miss` meaning).  
  **Scope and status:** validated for the non-visual path under test. This stage
  is not the current first-failure source in Lane A/B/C/D outcomes.

- `PDP = spm_MDP_generate(GDP);` then slice `PDP.O(:,1:k)` / `PDP.O(:,1:1000)`.  
  **Scope and status:** pre-structure-learning `PDP.O` parity gates pass in the
  current harness configuration. This comparability currently depends on MATLAB
  random-draw replay and is therefore not yet fully Python-native RNG behavior.

- Visual loop (`spm_figure`, `imshow`, `drawnow`).  
  **Out of scope** for this non-visual parity lane; not part of current bottleneck.

- `MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);`:
  - Grouping internals via `spm_rgm_group`:
    - `spm_MDP_MI` operation on runtime `o_sub` slices.  
      **Current bottleneck #1.** Temporary flag
      `RGMS_FSL_RGM_MATLAB_MI_PUSH=1` replaces Python `spm_MDP_MI`-derived MI
      matrix construction with MATLAB MI matrix construction for each active
      `o_sub` in `spm_rgm_group`.
    - Eigen decomposition and ranking operation used for group selection.  
      **Current bottleneck #2.** Temporary flag `RGMS_FSL_RGM_MATLAB_EIG=1`
      replaces Python/SciPy eig output with MATLAB `eig(...,'nobalance')`
      output in `spm_rgm_group`, isolating the eigenpair-and-ordering step.

  - Later link stage (`_link_streams`) writes `ss.ID` / `ss.IE` via `spm_dir_MI(a_mat)`.
    **Current bottleneck #3 (later than `spm_rgm_group`).** In observed Lane C
    first-failure evidence, the linked matrix bytes match exactly, but stored
    `ss.ID` scalar differs at key `(1,58)`: MATLAB `spm_dir_MI(a_mat)` returns
    `8.8817841970012523e-16` while Python `spm_dir_MI(a_mat)` returns `0.0`.
    Temporary flag `RGMS_FSL_LINK_DIR_MI_MATLAB=1` replaces this specific
    link-time `spm_dir_MI` scalar operation with MATLAB.

- Exhaustive nested canonical-byte compare (full tree gate).  
  Checkpoint controls:
  - `RGMS_FSL_USE_CHECKPOINT=1`
  - `RGMS_FSL_REFRESH_CHECKPOINT=1` (optional rebuild)  
  Checkpoint purpose is **speed/reproducibility only** (reuse `O_fsl_sx/S_fsl_sx`
  and `o_sl`), not algorithmic behavior change.

Current validated status at this progress point:

- Replay-controlled pre-`spm_faster_structure_learning` comparability is validated
  for the tested harness path; this still includes a MATLAB random-draw replay
  intervention.
- Bottleneck ordering in exhaustive Lane A/B/C/D evidence is currently:
  `spm_MDP_MI` operation in `spm_rgm_group` -> eig/ordering operation in
  `spm_rgm_group` -> link-time `spm_dir_MI` operation in `_link_streams`.
- With all three temporary replacements active (Lane D), exhaustive checkpoint
  passes; this is evidence of bottleneck localization, not evidence that the
  full path is already fully Python-native.


# 4. Test Lanes and current evaluation

Lane configurations:

- **Lane A:** exhaustive selector with `RGMS_FSL_RGM_MATLAB_EIG=0`,
  `RGMS_FSL_RGM_MATLAB_MI_PUSH=0`, `RGMS_FSL_LINK_DIR_MI_MATLAB=0` (native
  `spm_rgm_group` and native link-time `spm_dir_MI`).
- **Lane B:** exhaustive selector with `RGMS_FSL_RGM_MATLAB_EIG=0`,
  `RGMS_FSL_RGM_MATLAB_MI_PUSH=1`, `RGMS_FSL_LINK_DIR_MI_MATLAB=0`
  (MATLAB replacement for `spm_MDP_MI` operation in `spm_rgm_group`; eig and
  link-time `spm_dir_MI` remain native Python).
- **Lane C:** exhaustive selector with `RGMS_FSL_RGM_MATLAB_EIG=1`,
  `RGMS_FSL_RGM_MATLAB_MI_PUSH=1`, `RGMS_FSL_LINK_DIR_MI_MATLAB=0`
  (MATLAB replacement for `spm_MDP_MI` and eig operations in `spm_rgm_group`;
  link-time `spm_dir_MI` remains native Python).
- **Lane D:** exhaustive selector with `RGMS_FSL_RGM_MATLAB_EIG=1`,
  `RGMS_FSL_RGM_MATLAB_MI_PUSH=1`, `RGMS_FSL_LINK_DIR_MI_MATLAB=1`
  (MATLAB replacement for all three currently tracked operations:
  `spm_MDP_MI` in `spm_rgm_group`, eig in `spm_rgm_group`, and link-time
  `spm_dir_MI` in `_link_streams`).
- **Lane E:** non-exhaustive subset in this same file via
  `-k "not exhaustive_exact_oracle"`; this lane is for quick regression coverage
  and is not a full exhaustive bottleneck-classification lane.

Lane-to-bottleneck interpretation (current evidence from `log_0.md` lane reruns):

- **Lane A:** first failure occurs in `spm_rgm_group` group bytes, so downstream
  link-time `spm_dir_MI` is not yet the first failing operation in this lane.
- **Lane B:** replacing `spm_MDP_MI` operation alone does not clear first failure;
  first failure remains in `spm_rgm_group` group ordering output.
- **Lane C:** replacing both `spm_MDP_MI` and eig operations moves first failure
  to link-time `spm_dir_MI` storage (`ss.ID` mismatch at key `(1,58)`).
- **Lane D:** replacing `spm_MDP_MI`, eig, and link-time `spm_dir_MI` yields
  exhaustive pass on checkpointed inputs.
- **Lane E:** provides non-exhaustive regression information only; do not use it
  as standalone evidence for full exhaustive bottleneck classification.

Current progress toward end goal is substantial but intentionally staged. The
team can now isolate and discuss specific function-level operations by lane using
shared terminology (`spm_MDP_MI`, eig operation inside `spm_rgm_group`, and
link-time `spm_dir_MI`) instead of ambiguous shorthand.

The unresolved operations are currently:
1) native eig/ordering behavior in `spm_rgm_group`, and
2) native link-time `spm_dir_MI` near-cancellation behavior when writing `ss.ID/ss.IE`.
These are separable by lane evidence (Lane B still fails in `spm_rgm_group`,
Lane C moves first failure to link-time `spm_dir_MI`, Lane D passes with all
three temporary replacements active).

Going forward, closure criteria remain explicit: temporary MATLAB interventions
are investigative scaffolding, and completion requires documented, Python-native
behavior at these operations plus clear scope statements for what each passing
test selector proves.


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

# 6. Python-native versus MATLAB interventions

This section is the consolidated reference for every place the current structure-learning
subproject still uses MATLAB as a replacement or source of truth during execution.
Unlike `logs\log_0.md` (chronological run log), this table captures the current
state in one place with exact call sites, flags, mismatch evidence, and lane meaning.

| Ordered pipeline stage / call site | Python-native behavior (target) | Current MATLAB intervention (temporary) | Activation mechanism and files | Detailed mismatch / bottleneck evidence motivating intervention | Lanes where active | What a pass/fail means in this scope |
|---|---|---|---|---|---|---|
| `rng(2)` in MATLAB snippet intent (harness currently uses `rng(0,'twister')`) and subsequent `spm_MDP_generate` random draws | Python should eventually use native RNG semantics with a settled reproducibility policy and produce acceptable parity through Python-native behavior. | MATLAB generates a random draw buffer; Python consumes that buffer by patching `numpy.random.rand` replay order. This is a controlled replacement of Python RNG output stream. | In `tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py`: `_matlab_rand_buf_twister_np(...)` + `_rand_replay_callable(...)` + `with patch("numpy.random.rand", ...)` around `spm_MDP_generate(...)`. | Upstream stochastic variance must be removed before downstream SL bottlenecks can be attributed correctly. Without replay control, failures in `spm_faster_structure_learning` cannot be cleanly interpreted because `PDP.O` input differs first. | Used in generation-integrated tests and in exhaustive non-checkpoint rebuild path. Not an A/B/C/D flag by itself. | Pass in this scope means upstream `PDP.O` comparability is controlled for diagnostic isolation. It does **not** mean RNG semantics are fully Python-native yet. |
| `MDP = spm_faster_structure_learning(...)` -> inside `spm_rgm_group`: MI matrix construction via `spm_MDP_MI` on runtime `o_sub` slices | Native path computes MI in Python: `spm_rgm_group` builds `p = r_cells[i] @ r_cells[j].T`, then `_spm_mdp_mi_scalar(p)` -> `spm_MDP_MI(p)` in `python_src/spm_MDP_MI.py`. | MATLAB builds MI matrix for each current `o_sub` and injects it into Python `spm_rgm_group` as `mi_override`. This replaces native `spm_MDP_MI` use for grouping decisions. | Flag `RGMS_FSL_RGM_MATLAB_MI_PUSH=1`. Harness creates `rgm_mi_override_fn` via `_make_rgm_mi_override_fn_matlab(...)`; passed through `spm_faster_structure_learning(..., rgm_mi_override_fn=...)` in `python_src/toolbox/DEM/spm_faster_structure_learning.py`; consumed as `mi_override` in `python_src/toolbox/DEM/spm_rgm_group.py`. | Lane A/B evidence shows early mismatch around grouping path. In Lane A, first failure is `spm_rgm_group stream 1 group 2: canonical byte mismatch`, with MI decomposition diagnostics (example `MI(1,24)` delta around `-1.11e-16`) showing MI/eig sensitivity zone. Lane B (MI override on, eig native) still fails same boundary, proving `spm_MDP_MI` replacement alone is insufficient. | B, C, D (off in A and E by default). | Pass with this bridge active only proves downstream can proceed when MATLAB `spm_MDP_MI` values are injected. Fail with this bridge active means residual divergence is elsewhere (observed: eig ordering still diverges in Lane B). |
| `MDP = spm_faster_structure_learning(...)` -> inside `spm_rgm_group`: eigen decomposition and group ordering (`[e,v]=eig(...)`, `sort(abs(e(:,jmax)),'descend')`) | Native path uses SciPy eig pipeline in `spm_rgm_group.py` (`spla.eig`) and Python sorting logic intended to mirror MATLAB ordering. | MATLAB `eig(...,'nobalance')` is called per active MI block and returned eigenpairs are injected into Python `spm_rgm_group` via `eig_pair` callback. | Flag `RGMS_FSL_RGM_MATLAB_EIG=1`. Harness `_make_matlab_rgm_eig_pair(...)`; passed via `spm_faster_structure_learning(..., rgm_eig_pair=...)`; used in `spm_rgm_group(..., eig_pair=...)`. | Lane A/B diagnostics show ULP-level near-tie ordering mismatch in iter2: same MI block yields different rank-1 selection (`mat_idx=74` vs `py_idx=38`) with tiny magnitude deltas (`max|am-ap| ~ 9.992e-16`, `max_ulps ~ 36`). Lane C moves first failure away from `spm_rgm_group` to later link stage, confirming this intervention clears the grouping-order bottleneck. | C, D (off in A/B/E by default). | Pass with this bridge active indicates grouping divergence is specifically tied to native eig/ordering behavior. It does **not** by itself validate native Python eig parity has been solved. |
| `MDP = spm_faster_structure_learning(...)` -> `_link_streams` writes `ss.ID` / `ss.IE` via `spm_dir_MI(a_mat)` | Native path computes link MI in Python with `spm_dir_MI(a_mat)` from `python_src/spm_dir_MI.py` when storing stream-link metadata. | MATLAB `spm_dir_MI` is called on each linked `a_mat` and returned scalar is used instead of native Python scalar for `ss.ID` / `ss.IE`. | Flag `RGMS_FSL_LINK_DIR_MI_MATLAB=1`. Harness creates `link_dir_mi_fn` via `_make_matlab_link_dir_mi_fn(...)`; passed into `spm_faster_structure_learning(..., link_dir_mi_fn=...)`; consumed by `_link_streams` `_stream_link_mi(...)` in `python_src/toolbox/DEM/spm_faster_structure_learning.py`. | Lane C first failure is explicit at `MDP{1}.ss.ID{1,2}(1,58): canonical byte mismatch`. Diagnostic details: linked matrix bytes match (`MDP{2}.a{21}` exact), but scalar differs: MATLAB `spm_dir_MI(...) = 8.8817841970012523e-16` while Python stores `0.0`; delta `-8.882e-16`. This identifies a near-cancellation numeric discrepancy at link-storage MI, not a matrix-construction mismatch. | D (off in A/B/C/E by default). | Pass with this bridge (Lane D) means full exhaustive tree parity can be achieved when link-time MI scalar is MATLAB-sourced. It proves bottleneck localization, not final native closure. |
| Exhaustive test input provisioning (`RGMS_FSL_USE_CHECKPOINT=1`) before calling Python/MATLAB `spm_faster_structure_learning` | Full native pipeline run would regenerate inputs each run from the ordered snippet path. | Checkpoint loads prebuilt `o_sl` and MATLAB `O_fsl_sx/S_fsl_sx` to skip expensive replay-generation and hold deterministic inputs fixed. | Flag `RGMS_FSL_USE_CHECKPOINT=1` (optional rebuild with `RGMS_FSL_REFRESH_CHECKPOINT=1`) in `tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py`; artifacts under `tests/oracle/toolbox/DEM/_checkpoint_data/`. | Not a numeric bottleneck itself; it is a reproducibility and runtime control. It prevents upstream stochastic or runtime drift from obscuring downstream bottleneck diagnosis and allows lane-to-lane comparability. | Common in A/B/C/D runs in this phase. | Pass/fail under checkpoint scope is about the SL and compare path on fixed inputs. It does not independently validate full upstream generation path on every run. |

### Scope clarification for team use

- A/B/C/D lane outcomes are statements about the exhaustive selector  
  `tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py::test_spm_faster_structure_learning_snippet_scale_T1000_exhaustive_exact_oracle`.
- `file.py::test_name` means "test function `test_name` inside `file.py`", not a separate file.
- Any claim of "validated" must state whether it is:
  1) upstream generation parity scope,  
  2) exhaustive SL-on-fixed-input scope, or  
  3) non-exhaustive regression subset scope (Lane E).
